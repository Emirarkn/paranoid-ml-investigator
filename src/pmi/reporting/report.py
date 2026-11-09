"""Report Generator — built ONLY from the ledger, profile and artifacts.

No number in this report comes from the LLM. The agent's own interpretation lives in
runs/<id>/notes/*.md and must pass `pmi check-claims`.
"""
from __future__ import annotations

import json
from typing import Any

from pmi.core.run import Run
from pmi.evidence.ledger import Ledger
from pmi.profiling.profile import load_profile

STATUS_ORDER = ["Verified", "Simulated", "Suspected", "Inconclusive", "Rejected"]
STATUS_MEANING = {"Verified": "Verified on real code/data with a reproducible test",
                  "Simulated": "Observed only under controlled experimental conditions",
                  "Suspected": "Plausible hypothesis, not tested yet",
                  "Inconclusive": "Test result insufficient for a decision",
                  "Rejected": "The experiment did not support the hypothesis"}


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _exp_block(run: Run, e: dict[str, Any]) -> list[str]:
    L = [f"- **{e['id']}** `{e['type']}` — state: {e['state']}, adapter: {e.get('adapter_kind') or '—'} "
         f"(fidelity: {e.get('adapter_fidelity') or '—'})"]
    L.append(f"  - Pre-registered decision rule: `{json.dumps(e['decision_rule'], ensure_ascii=False)}`")
    L.append(f"  - Spec: `{json.dumps(e['spec'], ensure_ascii=False)}`")
    if e["state"] == "failed":
        L.append(f"  - Error: `{e['error']}`")
        return L
    r = e["result"] or {}
    if e["type"] == "check":
        L.append(f"  - Result: defect_found={r.get('defect_found')} — {r.get('summary', '')}")
        refs = r.get("refs") or []
        if refs:
            L.append(f"  - References: {', '.join('`' + x + '`' for x in refs[:12])}")
    elif e["type"] == "baseline":
        mets = r.get("metrics", {})
        L.append("  - Baseline: " + ", ".join(f"{k}={_fmt(v.get('mean'))} [{_fmt(v.get('min'))}, {_fmt(v.get('max'))}]"
                                            for k, v in mets.items()))
        L.append(f"  - Reproduction: `{json.dumps(r.get('reproduction'), ensure_ascii=False)}`")
    elif e["type"] == "amplify":
        prim = r.get("primary_metric")
        L.append(f"  - Injector `{r.get('injector')}` on `{r.get('where')}`, columns {r.get('columns')}; "
                 f"base condition={_fmt(r.get('base_condition'))}; {r.get('ladder')}")
        L.append(f"  - Baseline seed noise (rel. std): {_fmt(r.get('baseline_noise_rel_std'))}")
        L.append("")
        L.append(f"  | Level | Condition (target) | Condition (realised) | {prim} mean [min,max] | EAF mean [min,max] | Failures | Limit |")
        L.append("  |---|---|---|---|---|---|---|")
        for row in r.get("levels", []):
            m, ea = row.get(prim) or {}, row.get(f"eaf_{prim}") or {}
            L.append(f"  | {row['label']} | {_fmt(row.get('condition'))} | {_fmt(row.get('condition_realized_mean'))} | "
                     f"{_fmt(m.get('mean'))} [{_fmt(m.get('min'))}, {_fmt(m.get('max'))}] | "
                     f"{_fmt(ea.get('mean'))} [{_fmt(ea.get('min'))}, {_fmt(ea.get('max'))}] | "
                     f"{row.get('failures', 0)}/{row.get('replicates', 0)} | {'EXCEEDED' if row.get('limit_exceeded') else ''} |")
        L.append("")
        L.append(f"  - Threshold discovery: `{json.dumps(r.get('threshold'), ensure_ascii=False)}`")
    elif e["type"] == "ablation":
        prim = r.get("primary_metric")
        L.append(f"  - Ablation `{r.get('mode')}` on `{r.get('where')}`")
        L.append(f"  | Step | {prim} | EAF mean [min,max] | Failures |")
        L.append("  |---|---|---|---|")
        for row in r.get("steps", []):
            ea = row.get(f"eaf_{prim}") or {}
            L.append(f"  | {row['step']} | {_fmt((row.get(prim) or {}).get('mean'))} | "
                     f"{_fmt(ea.get('mean'))} [{_fmt(ea.get('min'))}, {_fmt(ea.get('max'))}] | {row.get('failures', 0)} |")
    arts = e.get("artifacts") or []
    if arts:
        L.append("  - Evidence files: " + ", ".join(f"`artifacts/{e['id']}/{a['path']}` (sha256 {a['sha256'][:12]}…)"
                                               for a in arts))
    return L


def build_report(run: Run, ledger: Ledger) -> str:
    m = run.manifest
    prof = load_profile(run.profile_path)
    integ = run.integrity()
    chain = ledger.verify_chain()
    hyps = ledger.list_hypotheses()
    budget = run.budget_state(ledger.count_experiments())
    L: list[str] = ["# Paranoid ML Investigator — Audit Report", "",
                    f"- Run: `{run.id}`  •  Target: `{m['target_path']}`  •  Created: {m['created_at']}",
                    f"- pmi {m['pmi_version']}  •  Python {m['python']}  •  Packages: {m['packages']}",
                    f"- Target integrity (original files untouched?): **{'OK' if integ['ok'] else 'BROKEN'}**"
                    + ("" if integ["ok"] else f" — `{json.dumps(integ, ensure_ascii=False)[:400]}`"),
                    f"- Evidence ledger hash chain: **{'OK' if chain['ok'] else 'BROKEN'}**"
                    + ("" if chain["ok"] else f" — {chain['problems'][:5]}"),
                    f"- Adapter: {run.adapter_meta.get('kind', 'none')} / fidelity **{run.adapter_fidelity()}**",
                    f"- Budget: {budget['experiments_used']}/{budget['experiments_max']} experiments, "
                    f"{budget['minutes_used']}/{budget['minutes_max']} min", "",
                    "> This report is generated only from the evidence ledger. Every number comes from Python "
                    "experiments; LLM interpretation lives under `notes/` and is audited separately. Simulated results "
                    "are hypothetical stress scenarios, not production data. Correlation is not evidence of causation.", ""]

    L += ["## 1. Learned project profile", "", "| Field | Status | Value | Evidence |", "|---|---|---|---|"]
    for k, f in prof["fields"].items():
        val = f["value"] if f["status"] == "confirmed" else (f["candidates"][0]["value"] if f.get("candidates") else None)
        ev = f["evidence"] if f["status"] == "confirmed" else (f["candidates"][0]["evidence"] if f.get("candidates") else "")
        tag = {"confirmed": "confirmed", "proposed": "candidate (unconfirmed)", "unknown": "unknown"}[f["status"]]
        L.append(f"| {k} | {tag} | `{_fmt(val)}` | {str(ev or '')[:120]} |")
    unknown = [k for k, f in prof["fields"].items() if f["status"] != "confirmed"]
    if unknown:
        L += ["", f"Analyses requiring the unconfirmed fields ({', '.join(unknown)}) were **not run**."]

    counts = {s: sum(h["status"] == s for h in hyps) for s in STATUS_ORDER}
    L += ["", "## 2. Summary", "", "| Status | Meaning | Count |", "|---|---|---|"]
    L += [f"| {s} | {STATUS_MEANING[s]} | {counts[s]} |" for s in STATUS_ORDER]

    L += ["", "## 3. Findings", ""]
    for s in STATUS_ORDER:
        group = sorted([h for h in hyps if h["status"] == s], key=lambda h: (h["priority"], h["id"]))
        if not group:
            continue
        L += [f"### {s}", ""]
        for h in group:
            exps = ledger.list_experiments(h["id"])
            L += [f"#### {h['id']} — {h['title']}  `[{h['status']}]`", "",
                  f"- **Problem / claim:** {h['statement']}",
                  f"- **Mechanism (hypothesis):** {h['mechanism']}",
                  f"- **Expected effect:** {h['expected_effect']}",
                  f"- **Falsification test:** {h['falsification_test']}",
                  f"- **Kind / priority:** {h['kind']} / P{h['priority']}",
                  f"- **Source file/line:** {', '.join('`' + r + '`' for r in h['refs']) or '—'}",
                  f"- **Affected data:** {h['affected_data'] or '—'}",
                  f"- **Status reason (pmi verify):** {h['status_reason']}",
                  f"- **Proposed fix (proposal — untested):** {h['proposed_fix'] or '—'}",
                  "- **Experiments:**"]
            if not exps:
                L.append("  - (no experiment yet)")
            for e in exps:
                L += ["  " + x if not x.startswith("  ") else x for x in _exp_block(run, e)]
            L.append("")
    L += ["## 4. Limits and uncertainty", "",
          "- Amplification results measure the model's response when a condition is grown in a controlled way; they "
          "say nothing about how likely those levels are in the real world. Levels marked `EXCEEDED` were clamped at "
          "a physical/logical limit.",
          "- Levels labelled `A1/A2/A3` form an absolute ladder (base condition 0) and cannot be read as 'N times'.",
          "- If adapter fidelity is not 'confirmed', experiments run through the adapter can be at most Inconclusive.",
          "- The network guard is not an operating-system sandbox; see docs/PERMISSIONS.md.", ""]
    return "\n".join(L)
