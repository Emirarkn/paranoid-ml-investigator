"""Project Profile — what the agent has LEARNED about the investigated project.

The harness ships with no domain vocabulary (no "SKU", no "month", no "WAPE" assumed).
Every field starts `unknown`, scans add `candidates` with evidence, and only a human-approved
`pmi profile set` makes a field `confirmed`. Analyses that need an unconfirmed field are blocked.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from pmi.core.config import PMIError
from pmi.core.run import read_json, utcnow, write_json

FIELDS: dict[str, str] = {
    "task_type": "regression | classification | forecasting | ranking | llm | other — what is predicted",
    "data_source": "workspace-relative path of the modelling table (or 'adapter')",
    "unit_of_analysis": "what one row / one prediction represents, in the project's own words",
    "target": "column the model predicts",
    "time_column": "column that orders observations in time (or 'none')",
    "time_grain": "spacing of the time axis as found in the data (or 'none')",
    "entity_keys": "list of columns identifying a series / unit (or [])",
    "feature_columns": "list of model inputs",
    "feature_availability": "map feature -> known_at_prediction | future | unknown",
    "prediction_horizon": "how far ahead predictions are made (or 'none')",
    "evaluation_protocol": "how the project evaluates (split / backtest / CV), with source",
    "primary_metric": "metric the project optimises / reports",
    "reported_metric": "{metric, value, source} — the project's own claimed performance",
    "acceptable_threshold": "{metric, max|min} — when performance becomes unacceptable (business-defined)",
    "business_context": "how predictions are used downstream (decisions they drive)",
}


def empty_profile() -> dict[str, Any]:
    return {"updated_at": utcnow(),
            "fields": {k: {"status": "unknown", "value": None, "evidence": None,
                           "candidates": [], "description": d} for k, d in FIELDS.items()}}


def load_profile(path: Path) -> dict[str, Any]:
    prof = read_json(path)
    return prof if prof else empty_profile()


def _cand(value: Any, evidence: str, confidence: str) -> dict[str, Any]:
    return {"value": value, "evidence": evidence, "confidence": confidence}


def draft_from_scans(profile: dict[str, Any], data_scan: dict[str, Any], code_scan: dict[str, Any]) -> dict[str, Any]:
    """Refresh candidates (never touches confirmed fields)."""
    f = profile["fields"]
    cands: dict[str, list] = {k: [] for k in FIELDS}

    tables = {k: v for k, v in data_scan.get("tables", {}).items() if "error" not in v}
    for path, t in sorted(tables.items(), key=lambda kv: -kv[1]["n_columns"] * kv[1]["n_rows_scanned"]):
        cands["data_source"].append(_cand(path, f"{t['n_rows_scanned']} rows x {t['n_columns']} cols scanned", "low"))
        for tc in t["temporal_candidates"]:
            g = t["columns"][tc].get("temporal", {})
            cands["time_column"].append(_cand(tc, f"{path}: parses as datetime ({g.get('evidence', '')})", "medium"))
            if g.get("grain") and g["grain"] != "unknown":
                cands["time_grain"].append(_cand(g["grain"], f"{path}:{tc}: {g.get('evidence')}; "
                                                 f"{g.get('share_regular_steps')} of steps regular", "medium"))
        for kc in t["entity_key_candidates"]:
            if kc["keys"]:
                cands["entity_keys"].append(_cand(kc["keys"], f"{path}: {kc['evidence']}", "medium"))

    reads = Counter()
    for fr in code_scan.get("files", []):
        facts = fr.get("facts", {})
        for th in facts.get("target_hints", []):
            cands["target"].append(_cand(th["column"], f"{th['at']}: {th['code']}", "medium"))
        for fl in facts.get("feature_lists", []):
            cands["feature_columns"].append(_cand(fl["columns"], f"{fl['at']}: {fl['name']} = [...]", "medium"))
        for m in facts.get("metrics", []):
            cands["primary_metric"].append(_cand(m["metric"], f"{m['at']}", "low"))
        for s in facts.get("splits", []):
            cands["evaluation_protocol"].append(_cand(f"{s['call']}({', '.join(f'{k}={v}' for k, v in s['kwargs'].items())})",
                                                      s["at"], "medium"))
        for m in facts.get("models", []):
            name = m["class"]
            if name.endswith("Classifier") or name in ("LogisticRegression", "SVC"):
                cands["task_type"].append(_cand("classification", f"{m['at']}: {name}", "medium"))
            elif any(x in name for x in ("ARIMA", "SARIMAX", "Prophet", "ExponentialSmoothing", "Holt")):
                cands["task_type"].append(_cand("forecasting", f"{m['at']}: {name}", "medium"))
            elif name.endswith(("Regressor", "Regression")):
                cands["task_type"].append(_cand("regression", f"{m['at']}: {name}", "medium"))
        for r in facts.get("reads", []):
            reads[r["arg"]] += 1
    for arg, n in reads.most_common(3):
        cands["data_source"].insert(0, _cand(arg, f"read {n}x in project code", "medium"))

    for k, lst in cands.items():
        seen, uniq = set(), []
        for c in lst:
            key = repr(c["value"])
            if key not in seen:
                seen.add(key)
                uniq.append(c)
        if f[k]["status"] != "confirmed":
            f[k]["candidates"] = uniq[:8]
            f[k]["status"] = "proposed" if uniq else "unknown"
    profile["updated_at"] = utcnow()
    return profile


def set_field(profile: dict[str, Any], field: str, value: Any, evidence: str) -> dict[str, Any]:
    if field not in FIELDS:
        raise PMIError(f"Unknown profile field '{field}'. Valid: {', '.join(FIELDS)}")
    if not evidence or len(evidence.strip()) < 3:
        raise PMIError("--evidence is required (file:line, data fact, or 'user: <statement>').")
    entry = profile["fields"][field]
    entry.setdefault("history", []).append({"at": utcnow(), "old": entry.get("value"), "old_status": entry["status"]})
    entry.update({"status": "confirmed", "value": value, "evidence": evidence})
    profile["updated_at"] = utcnow()
    return profile


def get(profile: dict[str, Any], field: str, default: Any = None) -> Any:
    e = profile["fields"].get(field, {})
    return e.get("value") if e.get("status") == "confirmed" else default


def require(profile: dict[str, Any], fields: list[str]) -> None:
    missing = [k for k in fields if profile["fields"].get(k, {}).get("status") != "confirmed"]
    if missing:
        raise ProfileIncomplete(missing)


class ProfileIncomplete(PMIError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(
            "Blocked: these profile fields are not confirmed: " + ", ".join(missing) +
            ". Learn them from the project (see `pmi profile show`) and ask the human to confirm "
            "with `pmi profile set <field> <value> --evidence ...`. Do not guess.")


def save_profile(path: Path, profile: dict[str, Any]) -> None:
    write_json(path, profile)
