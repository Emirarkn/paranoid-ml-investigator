"""Evidence Verification Engine — the ONLY code path that changes a hypothesis status.

For every completed experiment of a hypothesis:
  1. artifact files exist and match their recorded sha256
  2. the pre-registered decision rule is evaluated on the recorded result
  3. replication: checks are re-executed in a fresh worker; model experiments have every
     metric recomputed from saved predictions with an independent implementation
  4. a status CAP is applied (what this kind of evidence is allowed to prove)
Then experiment outcomes are combined. Conflicting evidence -> Inconclusive.
"""
from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd

from pmi.core.config import PMIError, file_sha256
from pmi.core.run import Run
from pmi.engine import metrics as M
from pmi.engine.runner import run_job
from pmi.evidence.ledger import Ledger, canonical
from pmi.profiling.profile import load_profile

ORDER = {"Verified": 3, "Simulated": 2, "Inconclusive": 1}


def _artifacts_ok(run: Run, exp: dict[str, Any]) -> list[str]:
    bad = []
    for a in exp.get("artifacts") or []:
        p = run.artifacts / exp["id"] / a["path"]
        if not p.is_file():
            bad.append(f"missing artifact {a['path']}")
        elif file_sha256(p) != a["sha256"]:
            bad.append(f"artifact {a['path']} changed after the experiment")
    return bad


def _level_row(result: dict[str, Any], label: str, key: str) -> dict[str, Any] | None:
    rows = result.get("levels") or result.get("steps") or []
    if label == "max" and rows:
        return rows[-1]
    for r in rows:
        if r.get(key) == label:
            return r
    return None


def evaluate_rule(run: Run, exp: dict[str, Any]) -> dict[str, Any]:
    rule, res = exp["decision_rule"], exp["result"] or {}
    ev = run.policy.get("evidence", {})
    t = rule["type"]
    if t == "defect_found":
        return {"outcome": "pass" if res.get("defect_found") else "fail",
                "why": res.get("summary", ""), "numbers": {"defect_found": res.get("defect_found")}}
    if t == "baseline_gap":
        rep = res.get("reproduction", {})
        if "relative_gap" not in rep:
            return {"outcome": "inconclusive", "why": rep.get("error", "no reproduction data")}
        gap, tol = rep["relative_gap"], float(ev.get("baseline_reproduction_rel_tol", 0.02))
        if gap >= float(rule["min_relative_gap"]):
            return {"outcome": "pass", "why": f"reproduced {rep['reproduced']:.6g} vs reported {rep['reported']:.6g} "
                    f"(gap {gap:.2%})", "numbers": rep}
        if gap <= tol:
            return {"outcome": "fail", "why": f"reported metric reproduced within {tol:.0%} (gap {gap:.2%})", "numbers": rep}
        return {"outcome": "inconclusive", "why": f"gap {gap:.2%} between tolerance and rule threshold", "numbers": rep}
    if t == "eaf":
        metric = M.canonical_name(rule["metric"])
        key = "label" if exp["type"] == "amplify" else "step"
        row = _level_row(res, str(rule["level"]), key)
        if row is None:
            labels = [r.get(key) for r in (res.get("levels") or res.get("steps") or [])]
            return {"outcome": "inconclusive", "why": f"level '{rule['level']}' not in result (levels: {labels})"}
        e = row.get(f"eaf_{metric}") or {}
        n_rep = int(row.get("replicates", 0) or 0)
        min_rep = int(ev.get("min_replicates_for_simulated", 3))
        if row.get("failures"):
            return {"outcome": "pass", "why": f"model raised errors in {row['failures']} replicate(s) at {row.get(key)}",
                    "numbers": {"failures": row["failures"]}}
        if e.get("mean") is None:
            return {"outcome": "inconclusive", "why": f"no EAF for metric '{metric}' at {row.get(key)}"}
        if exp["type"] == "amplify" and n_rep < min_rep:
            return {"outcome": "inconclusive", "why": f"only {n_rep} replicate(s); policy needs {min_rep}"}
        noise = float(res.get("baseline_noise_rel_std", 0.0) or 0.0)
        floor = 1 + float(ev.get("noise_multiplier", 2.0)) * noise
        nums = {"metric": metric, "level": row.get(key), "eaf": e, "min_eaf": rule["min_eaf"], "noise_floor": floor,
                "condition": row.get("condition"), "limit_exceeded": row.get("limit_exceeded")}
        if e["mean"] >= float(rule["min_eaf"]) and (e.get("min") or 0) >= floor:
            return {"outcome": "pass", "why": f"EAF {e['mean']:.3g} (min {e['min']:.3g}) >= {rule['min_eaf']}", "numbers": nums}
        if (e.get("max") or 0) < float(rule["min_eaf"]):
            return {"outcome": "fail", "why": f"EAF max {e['max']:.3g} < {rule['min_eaf']}", "numbers": nums}
        return {"outcome": "inconclusive", "why": f"EAF range [{e['min']:.3g}, {e['max']:.3g}] straddles "
                f"{rule['min_eaf']} or the noise floor {floor:.3g}", "numbers": nums}
    return {"outcome": "inconclusive", "why": f"unknown rule type {t}"}


def _replicate(run: Run, exp: dict[str, Any]) -> list[str]:
    """Return a list of problems (empty = replication OK)."""
    problems: list[str] = []
    if exp["type"] == "check":
        profile = load_profile(run.profile_path)
        adapter = None
        if exp.get("adapter_kind"):
            meta = run.adapter_meta
            adapter = {"kind": meta.get("kind", "target"), "config": meta.get("config")}
        out = run_job(run, "check", exp["spec"], run.artifacts / exp["id"] / "verify_rerun", [0], adapter, profile)
        if not out.get("ok"):
            return [f"re-execution failed: {out.get('error')}"]
        a, b = exp["result"], out["result"]
        if a.get("defect_found") != b.get("defect_found") or canonical(a.get("observed")) != canonical(b.get("observed")):
            problems.append("re-executed check gives a different result (non-deterministic or inputs changed)")
        return problems
    pred = run.artifacts / exp["id"] / "predictions.csv.gz"
    if not pred.is_file():
        return ["no saved predictions to recompute from"]
    df = pd.read_csv(pred)
    tol = float(run.policy.get("evidence", {}).get("independent_recompute_rel_tol", 1e-6))
    res = exp["result"]
    names = res.get("metrics") if isinstance(res.get("metrics"), list) else list((res.get("metrics") or {}).keys())
    records_path = run.artifacts / exp["id"] / "records.json"
    if exp["type"] == "baseline":
        recorded = {(r["seed"], "baseline"): r["metrics"] for r in res.get("per_seed", [])}
    else:
        recs = json.loads(records_path.read_text(encoding="utf-8")) if records_path.is_file() else []
        key = "level" if exp["type"] == "amplify" else "step"
        recorded = {(r["seed"], r[key]): r.get("metrics", {}) for r in recs if "metrics" in r}
    checked = 0
    for (seed, level), mets in recorded.items():
        sub = df[(df["seed"] == seed) & (df["level"].astype(str) == str(level))]
        if sub.empty:
            problems.append(f"no predictions for seed={seed} level={level}")
            continue
        proba = sub["proba"].to_numpy() if sub["proba"].notna().all() else None
        for n in names:
            if n not in mets or mets[n] is None:
                continue
            try:
                v = M.recompute(n, sub["y_true"].to_numpy(), sub["y_pred"].to_numpy(), proba)
            except KeyError:
                continue
            ref = mets[n]
            if not (math.isnan(v) and ref is None) and abs(v - ref) > tol * max(1.0, abs(ref)):
                problems.append(f"{n} seed={seed} level={level}: recorded {ref:.10g} vs recomputed {v:.10g}")
            checked += 1
    if checked == 0:
        problems.append("nothing could be recomputed")
    return problems


def _cap(run: Run, hyp: dict[str, Any], exp: dict[str, Any]) -> tuple[str, str]:
    """Highest status this experiment may support, with the reason."""
    if hyp["kind"] == "sensitivity" or exp["type"] in ("amplify", "ablation"):
        cap, why = "Simulated", "controlled stress/ablation experiment (sensitivity, not an observed defect)"
    else:
        cap, why = "Verified", "deterministic check on project code/data"
    kind, fid = exp.get("adapter_kind"), exp.get("adapter_fidelity")
    if kind == "surrogate":
        return "Simulated", "surrogate model, not the project's own pipeline"
    if exp["type"] == "baseline":
        if run.adapter_meta.get("fidelity_source") != "human":
            return "Inconclusive", ("a reproduction gap can be the adapter's fault; Verified needs a human-confirmed "
                                    "adapter (pmi adapter confirm)")
        return cap, why
    if kind == "target" and fid != "confirmed":
        return "Inconclusive", (f"adapter fidelity was '{fid}' when this ran — the adapter is not proven to mirror the "
                                "project (reproduce the reported metric with pmi baseline, or human: pmi adapter confirm)")
    return cap, why


def verify(run: Run, ledger: Ledger, hid: str) -> dict[str, Any]:
    hyp = ledger.get_hypothesis(hid)
    exps = [e for e in ledger.list_experiments(hid) if e["state"] in ("done", "failed")]
    if not exps:
        raise PMIError(f"{hid} has no executed experiment. It stays Suspected.")
    integ = run.integrity()
    if not integ["ok"]:
        raise PMIError(f"Integrity check failed — target or workspace copy changed: {integ}. Stop and tell the human.")
    chain = ledger.verify_chain()
    if not chain["ok"]:
        raise PMIError(f"Ledger hash chain broken: {chain['problems']}. Stop and tell the human.")

    evals = []
    for exp in exps:
        if exp["state"] == "failed":
            evals.append({"experiment": exp["id"], "outcome": "inconclusive", "why": f"experiment failed: {exp['error']}",
                          "cap": "Inconclusive"})
            continue
        e: dict[str, Any] = {"experiment": exp["id"]}
        bad = _artifacts_ok(run, exp)
        if bad:
            e.update(outcome="inconclusive", why="; ".join(bad), cap="Inconclusive")
            evals.append(e)
            continue
        e.update(evaluate_rule(run, exp))
        cap, cap_why = _cap(run, hyp, exp)
        e.update(cap=cap, cap_reason=cap_why)
        reproduced_ok = exp["type"] == "baseline" and e["outcome"] == "fail"
        if cap == "Inconclusive" and e["outcome"] in ("pass", "fail") and not reproduced_ok:
            e.update(outcome="inconclusive", why=e["why"] + f" | capped: {cap_why}")
        if e["outcome"] in ("pass", "fail"):
            rep = _replicate(run, exp)
            e["replication"] = rep or "ok"
            if rep:
                e.update(outcome="inconclusive", why=e["why"] + " | replication failed: " + "; ".join(rep[:5]))
        evals.append(e)

    passes = [e for e in evals if e["outcome"] == "pass"]
    fails = [e for e in evals if e["outcome"] == "fail"]
    if passes and fails:
        status, reason = "Inconclusive", (f"conflicting evidence: pass in {[e['experiment'] for e in passes]}, "
                                          f"fail in {[e['experiment'] for e in fails]}")
    elif passes:
        best = max(passes, key=lambda e: ORDER.get(e["cap"], 0))
        status = best["cap"]
        reason = f"{best['experiment']}: {best['why']} [cap: {best['cap_reason']}]"
    elif fails:
        status = "Rejected"
        reason = "; ".join(f"{e['experiment']}: {e['why']}" for e in fails)
    else:
        status = "Inconclusive"
        reason = "; ".join(f"{e['experiment']}: {e['why']}" for e in evals)
    ledger._set_status(hid, status, reason, {"evaluations": evals,
                                              "experiments": [e["experiment"] for e in evals]})
    return {"hypothesis": hid, "status": status, "reason": reason, "evaluations": evals}
