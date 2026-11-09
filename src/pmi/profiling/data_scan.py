"""Data scan: describes tables WITHOUT assuming a domain.

Everything produced here is a *candidate* with the evidence that led to it. Whether a
column is "the time axis" or "the entity key" is decided later by the human/agent via
`pmi profile set` (status: confirmed).
"""
from __future__ import annotations

import itertools
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pmi.profiling.loaders import TABULAR, load_table


def _parse_datetime(s: pd.Series) -> pd.Series | None:
    """Return parsed datetimes if the column is (very likely) temporal, else None."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    nn = s.dropna()
    if nn.empty:
        return None
    if pd.api.types.is_numeric_dtype(s):
        if not pd.api.types.is_integer_dtype(nn):
            return None
        v = nn.astype("int64")
        # yyyymm or yyyymmdd style integer periods
        if v.between(190001, 210012).all() and (v % 100).between(1, 12).all():
            return pd.to_datetime(v.astype(str), format="%Y%m", errors="coerce").reindex(s.index)
        if v.between(19000101, 21001231).all():
            parsed = pd.to_datetime(v.astype(str), format="%Y%m%d", errors="coerce")
            if parsed.notna().mean() > 0.95:
                return parsed.reindex(s.index)
        return None
    if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
        return None
    sample = nn.astype(str).head(500)
    if sample.str.fullmatch(r"-?\d+(\.\d+)?").mean() > 0.5:   # plain numbers stored as text
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            parsed = pd.to_datetime(sample, errors="coerce")
    if parsed.notna().mean() < 0.9:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return pd.to_datetime(s, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            return pd.to_datetime(s, errors="coerce")


def infer_grain(dt: pd.Series) -> dict[str, Any]:
    u = pd.Series(dt.dropna().unique()).sort_values()
    if len(u) < 3:
        return {"grain": "unknown", "evidence": f"only {len(u)} distinct timestamps"}
    d = u.diff().dropna().dt.total_seconds() / 86400.0
    med = float(np.median(d))
    if med < 1 / 24 * 1.5:
        g = "sub-hourly"
    elif med < 0.9:
        g = "hourly/sub-daily"
    elif med <= 1.5:
        g = "daily"
    elif 6 <= med <= 8:
        g = "weekly"
    elif 27 <= med <= 32:
        g = "monthly"
    elif 88 <= med <= 93:
        g = "quarterly"
    elif 360 <= med <= 370:
        g = "yearly"
    else:
        g = "irregular"
    regular = float((np.abs(d - med) <= max(1.0, 0.1 * med)).mean())
    return {"grain": g, "median_step_days": round(med, 3), "share_regular_steps": round(regular, 3),
            "n_timestamps": int(len(u)), "min": str(u.iloc[0]), "max": str(u.iloc[-1]),
            "evidence": f"median gap between distinct timestamps = {med:.2f} days"}


def scan_table(df: pd.DataFrame) -> dict[str, Any]:
    n = len(df)
    cols: dict[str, Any] = {}
    temporal: dict[str, pd.Series] = {}
    for c in df.columns:
        s = df[c]
        nn = s.dropna()
        info: dict[str, Any] = {
            "dtype": str(s.dtype),
            "missing_rate": round(float(s.isna().mean()), 6) if n else None,
            "n_unique": int(nn.nunique()),
            "unique_ratio": round(float(nn.nunique() / max(len(nn), 1)), 6),
            "constant": bool(nn.nunique() <= 1),
        }
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            desc = nn.describe()
            info.update({k: (None if pd.isna(desc.get(k)) else round(float(desc.get(k)), 6))
                         for k in ("mean", "std", "min", "max")})
            info["share_zero"] = round(float((nn == 0).mean()), 6) if len(nn) else None
            info["share_negative"] = round(float((nn < 0).mean()), 6) if len(nn) else None
        dt = _parse_datetime(s)
        if dt is not None and dt.notna().mean() > 0.9:
            info["temporal_candidate"] = True
            info["temporal"] = infer_grain(dt)
            temporal[c] = dt
        cols[str(c)] = info

    # entity-key candidates: columns that, together with a time column, identify rows
    key_cands: list[dict[str, Any]] = []
    def _key_like(c) -> bool:
        k = df[c].nunique()
        if c in temporal or not 1 < k < max(2, n * 0.5) or pd.api.types.is_float_dtype(df[c]):
            return False
        if pd.api.types.is_numeric_dtype(df[c]):   # numeric codes only when low-cardinality
            return k <= max(50, int(0.05 * n))
        return True
    cat_like = [c for c in df.columns if _key_like(c)]
    for tcol in temporal:
        if df[tcol].nunique() == n:
            key_cands.append({"keys": [], "time": tcol, "row_unique_share": 1.0,
                              "evidence": f"{tcol} alone is unique per row (single series?)"})
        for k in (1, 2):
            for combo in itertools.combinations(cat_like[:12], k):
                share = 1 - df.duplicated(subset=[*combo, tcol]).mean()
                if share >= 0.99:
                    key_cands.append({"keys": list(map(str, combo)), "time": str(tcol),
                                      "row_unique_share": round(float(share), 4),
                                      "n_entities": int(df[list(combo)].drop_duplicates().shape[0]),
                                      "evidence": f"({', '.join(map(str, combo))}, {tcol}) unique for {share:.1%} of rows"})
            if any(c["time"] == str(tcol) and len(c["keys"]) == 1 for c in key_cands):
                break
    id_like = [str(c) for c in df.columns if n > 20 and cols[str(c)]["unique_ratio"] > 0.98
               and str(c) not in temporal and not pd.api.types.is_float_dtype(df[c])]
    return {"n_rows_scanned": n, "n_columns": df.shape[1], "columns": cols,
            "temporal_candidates": list(map(str, temporal)), "entity_key_candidates": key_cands[:10],
            "id_like_columns": id_like,
            "duplicate_row_share": round(float(df.duplicated().mean()), 6) if n else None}


def scan_data(copy_root: Path, inventory: dict[str, Any], max_rows: int) -> dict[str, Any]:
    tables: dict[str, Any] = {}
    for f in inventory["files"]:
        p = copy_root / f["path"]
        if not f.get("in_workspace") or p.suffix.lower() not in TABULAR:
            continue
        try:
            df = load_table(p, nrows=max_rows)
        except Exception as exc:  # unreadable or optional dependency missing
            tables[f["path"]] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        if df.shape[1] < 2:
            continue
        res = scan_table(df)
        res["truncated_to_rows"] = max_rows if len(df) >= max_rows else None
        tables[f["path"]] = res
    return {"tables": tables}
