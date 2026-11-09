"""pmi — command line of the Paranoid ML Investigator harness.

The agent drives the investigation exclusively through these commands. Commands that
need a human decision are listed as `ask` rules in .claude/settings.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pmi.core.config import PMIError, harness_root
from pmi.core.run import Run, read_json, write_json


def _out(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _json_arg(s: str) -> Any:
    if s.startswith("@"):
        return json.loads(Path(s[1:]).read_text(encoding="utf-8"))
    return json.loads(s)


def _value_arg(s: str) -> Any:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


def _ctx(args):
    from pmi.evidence.ledger import Ledger
    root = harness_root()
    run = Run.load(root, getattr(args, "run", None))
    return root, run, Ledger(run.ledger_path)


# ---------------------------------------------------------------------------
def cmd_init(args):
    from pmi.evidence.ledger import Ledger
    root = harness_root()
    run = Run.create(root, Path(args.target), args.name)
    Ledger(run.ledger_path)
    from pmi.profiling.profile import empty_profile, save_profile
    save_profile(run.profile_path, empty_profile())
    m = run.manifest
    _out({"run_id": run.id, "target": m["target_path"], "files_hashed": m["target_files"],
          "workspace_copy": m["workspace_copy"], "next": "pmi scan"})


def cmd_runs(args):
    root = harness_root()
    cur = (root / "runs" / "CURRENT").read_text(encoding="utf-8").strip() if (root / "runs" / "CURRENT").is_file() else None
    runs = sorted(p.name for p in (root / "runs").iterdir() if (p / "manifest.json").is_file())
    _out({"current": cur, "runs": runs})


def cmd_use(args):
    root = harness_root()
    Run.load(root, args.run_id)
    (root / "runs" / "CURRENT").write_text(args.run_id, encoding="utf-8")
    _out({"current": args.run_id})


def cmd_status(args):
    _, run, ledger = _ctx(args)
    from pmi.profiling.profile import load_profile
    prof = load_profile(run.profile_path)
    hyps = ledger.list_hypotheses()
    exps = ledger.list_experiments()
    _out({"run": run.id, "target": run.manifest["target_path"],
          "profile": {k: f["status"] for k, f in prof["fields"].items()},
          "adapter": {"kind": run.adapter_meta.get("kind"), "validated": run.adapter_meta.get("validated"),
                      "fidelity": run.adapter_fidelity()},
          "hypotheses": [{"id": h["id"], "status": h["status"], "title": h["title"]} for h in hyps],
          "experiments": [{"id": e["id"], "hyp": e["hypothesis_id"], "type": e["type"], "state": e["state"]} for e in exps],
          "budget": run.budget_state(ledger.count_experiments())})


def cmd_integrity(args):
    _, run, ledger = _ctx(args)
    res = run.integrity()
    res["ledger_chain"] = ledger.verify_chain()
    res["ok"] = res["ok"] and res["ledger_chain"]["ok"]
    _out(res)
    return 0 if res["ok"] else 3


def cmd_scan(args):
    _, run, _ = _ctx(args)
    from pmi.profiling.code_scan import scan_code
    from pmi.profiling.data_scan import scan_data
    from pmi.profiling.inventory import build_inventory
    from pmi.profiling.profile import draft_from_scans, load_profile, save_profile
    snap = read_json(run.snapshot_path, {})
    inv = build_inventory(run.target_copy, snap)
    write_json(run.scan_dir / "inventory.json", inv)
    max_rows = int(run.policy.get("execution", {}).get("max_rows_loaded_for_scan", 200000))
    data = scan_data(run.target_copy, inv, max_rows)
    write_json(run.scan_dir / "data_scan.json", data)
    temporal = {c for t in data["tables"].values() for c in t.get("temporal_candidates", [])}
    code = scan_code(run.target_copy, inv, temporal)
    write_json(run.scan_dir / "code_scan.json", code)
    prof = draft_from_scans(load_profile(run.profile_path), data, code)
    save_profile(run.profile_path, prof)
    _out({"inventory": inv["by_kind"], "tables": {k: (v.get("error") or f"{v['n_rows_scanned']}x{v['n_columns']}")
                                                  for k, v in data["tables"].items()},
          "static_suspicions": [{"pattern": p["pattern"], "at": p["at"], "confidence": p["confidence"]}
                                for p in code["patterns"]],
          "profile": {k: f["status"] for k, f in prof["fields"].items()},
          "files": ["scan/inventory.json", "scan/data_scan.json", "scan/code_scan.json", "profile.json"],
          "note": "Static suspicions are NOT findings. Register them as hypotheses and test them."})


def cmd_profile(args):
    _, run, _ = _ctx(args)
    from pmi.profiling.profile import FIELDS, load_profile, require, save_profile, set_field
    prof = load_profile(run.profile_path)
    if args.action == "show":
        if args.json:
            _out(prof)
        else:
            _out({k: ({"status": f["status"], "value": f["value"], "evidence": f["evidence"]}
                      if f["status"] == "confirmed" else {"status": f["status"], "candidates": f["candidates"][:5],
                                                          "means": FIELDS[k]})
                  for k, f in prof["fields"].items()})
    elif args.action == "set":
        prof = set_field(prof, args.field, _value_arg(args.value), args.evidence)
        save_profile(run.profile_path, prof)
        _out({args.field: prof["fields"][args.field]})
    elif args.action == "require":
        require(prof, args.fields)
        _out({"ok": True, "confirmed": args.fields})


def cmd_adapter(args):
    _, run, _ = _ctx(args)
    from pmi.evidence.experiments import adapter_confirm, adapter_validate
    if args.action == "validate":
        cfg = _json_arg(args.surrogate) if args.surrogate else None
        meta = adapter_validate(run, cfg)
        _out(meta)
        return 0 if meta["validated"] else 2
    if args.action == "confirm":
        _out(adapter_confirm(run, args.evidence))
    else:
        _out(dict(run.adapter_meta, current_fidelity=run.adapter_fidelity(), path=str(run.adapter_path)))


def cmd_hypothesis(args):
    _, run, ledger = _ctx(args)
    if args.action == "add":
        hid = ledger.add_hypothesis(title=args.title, statement=args.statement, mechanism=args.mechanism,
                                    expected_effect=args.expected or "", falsification_test=args.falsification,
                                    kind=args.kind, priority=args.priority, refs=args.refs or [],
                                    affected_data=args.affected or "", proposed_fix=args.fix or "")
        _out({"id": hid, "status": "Suspected", "next": f"pmi experiment plan --hypothesis {hid} ..."})
    elif args.action == "list":
        _out([{k: h[k] for k in ("id", "status", "kind", "priority", "title", "status_reason")}
              for h in ledger.list_hypotheses()])
    elif args.action == "show":
        h = ledger.get_hypothesis(args.id)
        h["experiments"] = [{k: e[k] for k in ("id", "type", "state", "decision_rule")} for e in ledger.list_experiments(args.id)]
        _out(h)
    elif args.action == "fix":
        ledger.update_fix(args.id, args.text)
        _out({"id": args.id, "proposed_fix": args.text, "note": "recorded as an untested proposal"})


def cmd_experiment(args):
    _, run, ledger = _ctx(args)
    from pmi.evidence.experiments import execute, plan
    if args.action == "plan":
        eid = plan(run, ledger, args.hypothesis, args.type, _json_arg(args.spec), _json_arg(args.rule))
        _out({"id": eid, "state": "planned", "next": f"pmi experiment run {eid}"})
    elif args.action == "run":
        e = execute(run, ledger, args.id)
        _out({k: e[k] for k in ("id", "state", "error", "result", "adapter_kind", "adapter_fidelity")})
        return 0 if e["state"] == "done" else 2
    elif args.action == "show":
        _out(ledger.get_experiment(args.id))
    elif args.action == "list":
        _out([{k: e[k] for k in ("id", "hypothesis_id", "type", "state")} for e in ledger.list_experiments()])


def cmd_baseline(args):
    _, run, ledger = _ctx(args)
    from pmi.evidence.experiments import execute, plan
    hid = next((h["id"] for h in ledger.list_hypotheses() if h["title"].startswith("[baseline]")), None)
    if hid is None:
        hid = ledger.add_hypothesis(
            title="[baseline] Reported performance cannot be reproduced",
            statement="The performance the project reports cannot be reproduced by re-running its pipeline.",
            mechanism="Report computed on different data/split/code version, leakage in the original run, or a "
                      "faithless adapter.",
            expected_effect="Reproduced metric differs from the reported metric by more than tolerance.",
            falsification_test="Re-run the pipeline through the adapter and compare to profile.reported_metric.",
            kind="defect", priority=1, origin="harness")
    eid = plan(run, ledger, hid, "baseline", {"replicates": args.replicates},
               {"type": "baseline_gap", "min_relative_gap": args.min_gap})
    e = execute(run, ledger, eid)
    _out({"hypothesis": hid, "experiment": eid, "state": e["state"], "error": e["error"],
          "result": e["result"], "adapter_fidelity_now": run.adapter_fidelity()})
    return 0 if e["state"] == "done" else 2


def cmd_verify(args):
    _, run, ledger = _ctx(args)
    from pmi.evidence.verify import verify
    _out(verify(run, ledger, args.id))


def cmd_report(args):
    _, run, ledger = _ctx(args)
    from pmi.reporting.report import build_report
    text = build_report(run, ledger)
    out = Path(args.out) if args.out else run.dir / "report.md"
    out.write_text(text, encoding="utf-8")
    _out({"report": str(out)})


def cmd_check_claims(args):
    _, run, ledger = _ctx(args)
    from pmi.reporting.claims import check_claims
    issues = check_claims(run, ledger, Path(args.file))
    _out({"file": args.file, "issues": issues, "ok": not issues})
    return 0 if not issues else 1


def cmd_catalog(args):
    if args.which == "checks":
        from pmi.auditors.checks import CHECKS
        _out({k: {"description": c.description, "requires_profile": c.requires,
                  "needs_split(adapter)": c.needs_split} for k, c in CHECKS.items()})
    else:
        from pmi.engine.injectors import INJECTORS
        _out({k: {"description": i.description, "ladder": i.ladder, "requires_profile": i.requires,
                  "numeric_only": i.numeric_only} for k, i in INJECTORS.items()})


def cmd_budget(args):
    _, run, ledger = _ctx(args)
    if args.action == "extend":
        run.extend_budget(args.experiments, args.minutes, args.reason)
    _out(run.budget_state(ledger.count_experiments()))


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pmi", description="Paranoid ML Investigator harness")
    p.add_argument("--run", help="run id (default: runs/CURRENT)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="[human gate] start a run on a target project (read-only)")
    s.add_argument("--target", required=True)
    s.add_argument("--name")
    s.set_defaults(fn=cmd_init)

    sub.add_parser("runs", help="list runs").set_defaults(fn=cmd_runs)
    s = sub.add_parser("use", help="switch current run")
    s.add_argument("run_id")
    s.set_defaults(fn=cmd_use)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("integrity", help="hash-check target, workspace copy and ledger chain").set_defaults(fn=cmd_integrity)
    sub.add_parser("scan", help="inventory + data scan + code scan -> profile candidates").set_defaults(fn=cmd_scan)

    s = sub.add_parser("profile")
    s.add_argument("action", choices=["show", "set", "require"])
    s.add_argument("field", nargs="?")
    s.add_argument("value", nargs="?")
    s.add_argument("fields", nargs="*")
    s.add_argument("--evidence")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_profile)

    s = sub.add_parser("adapter", help="validate [human gate: executes project code] | confirm [human gate] | show")
    s.add_argument("action", choices=["validate", "confirm", "show"])
    s.add_argument("--surrogate", help="JSON or @file: surrogate config (no runnable project pipeline)")
    s.add_argument("--evidence", help="for confirm: why the human believes the adapter mirrors the project")
    s.set_defaults(fn=cmd_adapter)

    s = sub.add_parser("hypothesis")
    s.add_argument("action", choices=["add", "list", "show", "fix"])
    s.add_argument("id", nargs="?")
    s.add_argument("--title")
    s.add_argument("--statement")
    s.add_argument("--mechanism")
    s.add_argument("--expected")
    s.add_argument("--falsification")
    s.add_argument("--kind", choices=["defect", "sensitivity"], default="defect")
    s.add_argument("--priority", type=int, default=3)
    s.add_argument("--refs", nargs="*")
    s.add_argument("--affected")
    s.add_argument("--fix")
    s.add_argument("--text")
    s.set_defaults(fn=cmd_hypothesis)

    s = sub.add_parser("experiment")
    s.add_argument("action", choices=["plan", "run", "show", "list"])
    s.add_argument("id", nargs="?")
    s.add_argument("--hypothesis")
    s.add_argument("--type", choices=["check", "baseline", "amplify", "ablation"])
    s.add_argument("--spec", help="JSON or @file")
    s.add_argument("--rule", help="pre-registered decision rule, JSON or @file")
    s.set_defaults(fn=cmd_experiment)

    s = sub.add_parser("baseline", help="reproduce the project's reported performance via the adapter")
    s.add_argument("--replicates", type=int, default=3)
    s.add_argument("--min-gap", type=float, default=0.05)
    s.set_defaults(fn=cmd_baseline)

    s = sub.add_parser("verify", help="evaluate evidence and set status (the only way a status changes)")
    s.add_argument("id")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("report")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("check-claims", help="audit an agent-written markdown file against the ledger")
    s.add_argument("file")
    s.set_defaults(fn=cmd_check_claims)

    s = sub.add_parser("checks", help="list structural checks")
    s.set_defaults(fn=cmd_catalog, which="checks")
    s = sub.add_parser("injectors", help="list fault injectors")
    s.set_defaults(fn=cmd_catalog, which="injectors")

    s = sub.add_parser("budget", help="show | extend [human gate]")
    s.add_argument("action", choices=["show", "extend"])
    s.add_argument("--experiments", type=int, default=0)
    s.add_argument("--minutes", type=float, default=0)
    s.add_argument("--reason", default="")
    s.set_defaults(fn=cmd_budget)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "profile":
        if args.action == "set" and (not args.field or args.value is None):
            print("usage: pmi profile set <field> <value> --evidence '...'", file=sys.stderr)
            return 2
        if args.action == "require":
            args.fields = [x for x in [args.field, args.value, *args.fields] if x]
    try:
        rc = args.fn(args)
        return int(rc or 0)
    except PMIError as exc:
        print(f"pmi: {exc}", file=sys.stderr)
        return 2
