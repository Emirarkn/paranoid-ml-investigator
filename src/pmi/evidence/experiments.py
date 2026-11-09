"""Planning (pre-registration) and execution of experiments."""
from __future__ import annotations

from typing import Any

from pmi.auditors.checks import CHECKS
from pmi.core.config import PMIError, load_amplification
from pmi.core.run import Run, read_json, utcnow, write_json
from pmi.engine.injectors import INJECTORS
from pmi.engine.runner import run_job
from pmi.evidence.ledger import Ledger
from pmi.profiling.profile import load_profile, require

TYPES = ("check", "baseline", "amplify", "ablation")
RULES_FOR = {"check": {"defect_found"}, "baseline": {"baseline_gap"},
             "amplify": {"eaf"}, "ablation": {"eaf"}}


def _adapter_ready(run: Run) -> bool:
    meta = run.adapter_meta
    return bool(meta) and meta.get("validated") and run.adapter_fidelity() != "stale"


def validate_spec(run: Run, etype: str, spec: dict[str, Any], rule: dict[str, Any]) -> None:
    if etype not in TYPES:
        raise PMIError(f"type must be one of {TYPES}")
    rtype = (rule or {}).get("type")
    if rtype not in RULES_FOR[etype]:
        raise PMIError(f"Decision rule for '{etype}' must have type in {sorted(RULES_FOR[etype])} "
                       f"(pre-registration is mandatory). See .claude/skills/experiment-design.")
    profile = load_profile(run.profile_path)
    if etype == "check":
        name = spec.get("check")
        if name not in CHECKS:
            raise PMIError(f"Unknown check '{name}'. Available: {', '.join(CHECKS)}")
        require(profile, CHECKS[name].requires)
        if CHECKS[name].needs_split and not _adapter_ready(run):
            raise PMIError(f"Check '{name}' needs the project's split: validate an adapter first.")
        if CHECKS[name].needs_data and not _adapter_ready(run) and spec.get("data_via") != "profile":
            require(profile, ["data_source"])
    else:
        if not _adapter_ready(run):
            raise PMIError(f"'{etype}' runs the model: register and validate an adapter first (pmi adapter validate).")
        require(profile, ["target", "task_type"])
    if etype == "amplify":
        inj = spec.get("injector")
        if inj not in INJECTORS:
            raise PMIError(f"Unknown injector '{inj}'. Available: {', '.join(INJECTORS)}")
        require(profile, INJECTORS[inj].requires)
        if not spec.get("columns"):
            raise PMIError("amplify spec needs 'columns' (which inputs carry the amplified condition).")
        if spec.get("where", "test") not in ("test", "train", "both"):
            raise PMIError("where must be test | train | both")
    if etype == "ablation" and not spec.get("features"):
        raise PMIError("ablation spec needs 'features'.")
    if rtype == "eaf":
        for k in ("metric", "level", "min_eaf"):
            if k not in rule:
                raise PMIError(f"eaf rule needs '{k}' (e.g. {{\"type\":\"eaf\",\"metric\":\"mae\",\"level\":\"3x\",\"min_eaf\":1.5}})")
    if rtype == "baseline_gap" and "min_relative_gap" not in rule:
        raise PMIError("baseline_gap rule needs 'min_relative_gap'.")


def plan(run: Run, ledger: Ledger, hid: str, etype: str, spec: dict, rule: dict) -> str:
    validate_spec(run, etype, spec, rule)
    return ledger.plan_experiment(hid, etype, spec, rule)


def seeds_for(run: Run, etype: str, spec: dict[str, Any]) -> list[int]:
    amp = load_amplification(run.root)
    default = 1 if etype == "check" else int(amp.get("default_replicates", 3))
    n = int(spec.get("replicates", default))
    mx = int(run.policy.get("budgets", {}).get("max_replicates", 10))
    if n > mx:
        raise PMIError(f"replicates={n} exceeds policy budgets.max_replicates={mx}")
    s0 = int(spec.get("seed", 0))
    return [s0 + i for i in range(n)]


def adapter_for_job(run: Run, etype: str, spec: dict[str, Any]) -> dict[str, Any] | None:
    if etype == "check":
        chk = CHECKS[spec["check"]]
        if not (chk.needs_data or chk.needs_split):
            return None
        if spec.get("data_via") == "profile" and not chk.needs_split:
            return None
        if not _adapter_ready(run):
            return None
    meta = run.adapter_meta
    return {"kind": meta.get("kind", "target"), "config": meta.get("config")}


def execute(run: Run, ledger: Ledger, eid: str) -> dict[str, Any]:
    exp = ledger.get_experiment(eid)
    if exp["state"] != "planned":
        raise PMIError(f"{eid} is '{exp['state']}'. Experiments run once; plan a new one to repeat.")
    budget = run.budget_state(ledger.count_experiments())
    if budget["exhausted"]:
        raise PMIError(f"Budget exhausted ({budget}). Ask the human: pmi budget extend ...")
    etype, spec = exp["type"], exp["spec"]
    validate_spec(run, etype, spec, exp["decision_rule"])  # profile/adapter may have changed since planning
    seeds = seeds_for(run, etype, spec)
    adapter = adapter_for_job(run, etype, spec)
    kind = adapter["kind"] if adapter else None
    fidelity = run.adapter_fidelity() if adapter else "n/a"
    ledger.mark_started(eid, kind, run.adapter_hash() if kind == "target" else None, fidelity)
    profile = load_profile(run.profile_path)
    out = run_job(run, etype, spec, run.artifacts / eid, seeds, adapter, profile)
    if out.get("ok"):
        ledger.mark_finished(eid, out["result"], out.get("artifacts", []), None)
        if etype == "baseline":
            _update_fidelity_from_baseline(run, out["result"])
    else:
        ledger.mark_finished(eid, None, [], out.get("error", "unknown error"))
    return ledger.get_experiment(eid)


def _update_fidelity_from_baseline(run: Run, result: dict[str, Any]) -> None:
    meta = run.adapter_meta
    if not meta or meta.get("fidelity_source") == "human":
        return
    rep = result.get("reproduction", {})
    tol = float(run.policy.get("evidence", {}).get("baseline_reproduction_rel_tol", 0.02))
    if "relative_gap" in rep:
        meta["fidelity"] = "confirmed" if rep["relative_gap"] <= tol else "mismatch"
        meta["fidelity_source"] = "baseline_reproduction"
        meta["fidelity_evidence"] = rep
        meta["fidelity_at"] = utcnow()
        write_json(run.adapter_meta_path, meta)


def adapter_validate(run: Run, surrogate_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Executes project code for the first time (human gate)."""
    adapter = {"kind": "surrogate", "config": surrogate_cfg} if surrogate_cfg else {"kind": "target"}
    profile = load_profile(run.profile_path)
    out = run_job(run, "validate", {}, run.dir / "adapter_validation", [0], adapter, profile)
    meta = {"kind": adapter["kind"], "config": surrogate_cfg, "validated": bool(out.get("ok")),
            "validated_at": utcnow(), "sha256": run.adapter_hash() if not surrogate_cfg else None,
            "validation": out.get("result") or {"error": out.get("error"), "traceback": out.get("traceback")},
            "fidelity": "surrogate" if surrogate_cfg else "unconfirmed"}
    old = read_json(run.adapter_meta_path, {})
    if old.get("fidelity_source") == "human" and old.get("sha256") == meta["sha256"]:
        meta.update({k: old[k] for k in ("fidelity", "fidelity_source", "fidelity_evidence", "fidelity_at")})
    write_json(run.adapter_meta_path, meta)
    if meta["validated"]:
        tgt = (out.get("result") or {}).get("target")
        pt = profile["fields"]["target"]
        if pt["status"] == "confirmed" and pt["value"] != tgt:
            meta["warning"] = f"adapter.target={tgt!r} differs from confirmed profile target={pt['value']!r}"
            write_json(run.adapter_meta_path, meta)
    return meta


def adapter_confirm(run: Run, evidence: str) -> dict[str, Any]:
    meta = run.adapter_meta
    if not meta or not meta.get("validated"):
        raise PMIError("Validate the adapter first.")
    if meta.get("kind") == "surrogate":
        raise PMIError("A surrogate can never be confirmed as faithful to the project.")
    meta.update({"fidelity": "confirmed", "fidelity_source": "human", "fidelity_evidence": evidence,
                 "fidelity_at": utcnow(), "sha256": run.adapter_hash()})
    write_json(run.adapter_meta_path, meta)
    return meta
