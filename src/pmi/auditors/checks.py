"""Deterministic structural checks. Each returns
   {"defect_found": bool, "observed": {...}, "refs": [...], "summary": str}
`defect_found=True` means the SUSPECTED problem is present in the real code/data.
Checks never guess profile values: required fields come from the confirmed profile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from pmi.profiling.code_scan import scan_file


@dataclass
class Check:
    name: str
    description: str
    fn: Callable[..., dict[str, Any]]
    requires: list[str] = field(default_factory=list)
    needs_data: bool = True
    needs_split: bool = False


def _to_time(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    if pd.api.types.is_integer_dtype(s) and s.dropna().between(190001, 210012).all():
        return pd.to_datetime(s.astype(str), format="%Y%m", errors="coerce")
    return pd.to_datetime(s, errors="coerce", format="mixed")


# ---------------------------------------------------------------------------
def static_patterns(ctx: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    root = Path(ctx["workspace"]) / "target"
    wanted = set(params.get("patterns") or [])
    files = params.get("files") or [p.relative_to(root).as_posix() for p in root.rglob("*")
                                    if p.suffix.lower() in (".py", ".ipynb")]
    temporal = set(params.get("temporal_names") or [])
    if ctx["profile"].get("time_column"):
        temporal.add(str(ctx["profile"]["time_column"]))
    hits = []
    for rel in sorted(files):
        res = scan_file(root / rel, rel, temporal)
        for p in res.get("patterns", []):
            if not wanted or p["pattern"] in wanted:
                hits.append(dict(p, file=rel))
    return {"defect_found": bool(hits), "observed": {"matches": hits, "files_scanned": len(files)},
            "refs": [h["at"] for h in hits],
            "summary": f"{len(hits)} static pattern match(es) in {len(files)} file(s)"}


def key_uniqueness(ctx, params):
    df = ctx["df"]
    keys = list(ctx["profile"].get("entity_keys") or [])
    t = ctx["profile"].get("time_column")
    cols = keys + ([t] if t and t != "none" else [])
    if not cols:
        raise ValueError("entity_keys and time_column are both empty/none; nothing to check")
    dup = df.duplicated(subset=cols, keep=False)
    ex = df.loc[dup, cols].head(5).astype(str).to_dict("records")
    return {"defect_found": bool(dup.any()), "observed": {"key": cols, "duplicate_rows": int(dup.sum()),
            "share": float(dup.mean()), "examples": ex}, "refs": [f"data:{'+'.join(cols)}"],
            "summary": f"{int(dup.sum())} rows share a ({', '.join(cols)}) key"}


def target_proxy(ctx, params):
    df, prof = ctx["df"], ctx["profile"]
    y = prof["target"]
    thr = float(params.get("threshold", 0.98))
    max_lag = int(params.get("max_future_lag", 3))
    exclude = set(params.get("exclude", [])) | {y}
    cols = params.get("columns") or [c for c in df.columns if c not in exclude
                                     and pd.api.types.is_numeric_dtype(df[c])]
    yv = pd.to_numeric(df[y], errors="coerce")
    tcol, keys = prof.get("time_column"), prof.get("entity_keys")
    future, past = {}, {}
    if tcol and tcol != "none" and keys is not None:
        order = df.assign(__t=_to_time(df[tcol])).sort_values([*keys, "__t"]).index
        s = df.loc[order]
        g = s.groupby(list(keys), sort=False)[y] if keys else None
        for k in range(1, max_lag + 1):
            future[k] = (g.shift(-k) if g is not None else s[y].shift(-k)).reindex(df.index)
            past[k] = (g.shift(k) if g is not None else s[y].shift(k)).reindex(df.index)
    hits = []
    for c in cols:
        x = pd.to_numeric(df[c], errors="coerce")
        m = x.notna() & yv.notna()
        if m.sum() < 10 or x[m].nunique() < 2:
            continue
        r0 = float(np.corrcoef(x[m], yv[m])[0, 1])
        eq = float((x[m] == yv[m]).mean())
        rec = {"column": c, "corr_with_target": round(r0, 4), "share_equal_to_target": round(eq, 4)}
        flagged = abs(r0) >= thr or eq >= 0.99
        # A legitimate lag feature (PAST target) also correlates with the current target.
        for k, py in past.items():
            mm = x.notna() & py.notna()
            if mm.sum() >= 10 and py[mm].nunique() > 1 and eq < 0.99:
                rp = float(np.corrcoef(x[mm], py[mm])[0, 1])
                if abs(rp) >= max(abs(r0) + 0.02, 0.9) or float((x[mm] == py[mm]).mean()) >= 0.99:
                    rec.update({"explained_by_past_target_lag": k, "corr_with_past_target": round(rp, 4)})
                    flagged = False
                    break
        for k, fy in future.items():
            mm = x.notna() & fy.notna()
            if mm.sum() >= 10 and fy[mm].nunique() > 1:
                rk = float(np.corrcoef(x[mm], fy[mm])[0, 1])
                eqk = float((x[mm] == fy[mm]).mean())
                if (abs(rk) >= thr and abs(rk) > abs(r0) + 0.02) or eqk >= 0.99:
                    rec.update({"matches_future_target_lag": k, "corr_with_future_target": round(rk, 4),
                                "share_equal_to_future_target": round(eqk, 4)})
                    flagged = True
                    break
        if flagged:
            hits.append(rec)
    return {"defect_found": bool(hits), "observed": {"threshold": thr, "flagged": hits, "columns_tested": len(cols),
            "future_check": bool(future)}, "refs": [f"data:{h['column']}" for h in hits],
            "summary": f"{len(hits)} feature(s) behave like the target or a future target"}


def temporal_overlap(ctx, params):
    df, tr, te = ctx["df"], ctx["train_idx"], ctx["test_idx"]
    t = _to_time(df[ctx["profile"]["time_column"]])
    tmin_test = t.loc[te].min()
    later = t.loc[tr] >= tmin_test
    share = float(later.mean())
    tol = float(params.get("tolerance_share", 0.0))
    tmax_train = t.loc[tr].max()
    test_with_future_train = float((t.loc[te] < tmax_train).mean())
    return {"defect_found": share > tol, "observed": {
        "share_of_test_rows_older_than_latest_train_row": round(test_with_future_train, 6),
        "train_range": [str(t.loc[tr].min()), str(t.loc[tr].max())],
        "test_range": [str(tmin_test), str(t.loc[te].max())],
        "train_rows_at_or_after_test_start": int(later.sum()), "share": round(share, 6)},
        "refs": ["adapter:split"], "summary": f"{share:.1%} of training rows are at/after the first test timestamp"}


def split_duplicates(ctx, params):
    df, tr, te = ctx["df"], ctx["train_idx"], ctx["test_idx"]
    cols = [c for c in df.columns if c not in set(params.get("exclude", []))]
    a = df.loc[tr, cols].astype(str).agg("|".join, axis=1)
    b = df.loc[te, cols].astype(str).agg("|".join, axis=1)
    n = int(b.isin(set(a)).sum())
    return {"defect_found": n > int(params.get("tolerance_rows", 0)),
            "observed": {"test_rows_identical_to_a_train_row": n, "share_of_test": round(n / max(len(b), 1), 6),
                         "columns_compared": cols},
            "refs": ["adapter:split"], "summary": f"{n} test rows are exact copies of training rows"}


def entity_overlap(ctx, params):
    df, tr, te = ctx["df"], ctx["train_idx"], ctx["test_idx"]
    keys = list(ctx["profile"]["entity_keys"])
    if not keys:
        raise ValueError("entity_keys is empty")
    a = set(map(tuple, df.loc[tr, keys].astype(str).to_numpy()))
    b = set(map(tuple, df.loc[te, keys].astype(str).to_numpy()))
    share = len(a & b) / max(len(b), 1)
    expect_disjoint = bool(params.get("expect_disjoint", False))
    return {"defect_found": expect_disjoint and share > 0,
            "observed": {"test_entities": len(b), "also_in_train": len(a & b), "share": round(share, 6),
                         "expect_disjoint": expect_disjoint},
            "refs": ["adapter:split"], "summary": f"{share:.1%} of test entities also appear in training"}


def missing_rates(ctx, params):
    df = ctx["df"]
    mx = float(params.get("max_rate", 0.2))
    rates = df.isna().mean().sort_values(ascending=False)
    bad = {str(k): round(float(v), 6) for k, v in rates.items() if v > mx}
    return {"defect_found": bool(bad), "observed": {"max_rate": mx, "above": bad,
            "all": {str(k): round(float(v), 6) for k, v in rates.items()}},
            "refs": [f"data:{k}" for k in bad], "summary": f"{len(bad)} column(s) above {mx:.0%} missing"}


CHECKS: dict[str, Check] = {
    "static_patterns": Check("static_patterns", "AST scan of project code for leakage/evaluation smells "
                             "(fit before split, fit on test, shuffled split on temporal data, negative shift).",
                             static_patterns, needs_data=False),
    "key_uniqueness": Check("key_uniqueness", "Rows are unique per (entity_keys, time_column).",
                            key_uniqueness, requires=["entity_keys", "time_column"]),
    "target_proxy": Check("target_proxy", "A feature ~equals the target or a FUTURE value of the target.",
                          target_proxy, requires=["target"]),
    "temporal_overlap": Check("temporal_overlap", "Training rows dated at/after the start of the test period.",
                              temporal_overlap, requires=["time_column"], needs_split=True),
    "split_duplicates": Check("split_duplicates", "Test rows that are exact copies of training rows.",
                              split_duplicates, needs_split=True),
    "entity_overlap": Check("entity_overlap", "Test entities seen in training (defect only if expect_disjoint).",
                            entity_overlap, requires=["entity_keys"], needs_split=True),
    "missing_rates": Check("missing_rates", "Columns whose missing share exceeds max_rate.", missing_rates),
}
