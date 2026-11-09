"""Fault injectors. Each one amplifies a CONDITION (cause), never the error.

Contract:
  base_condition(df, rows, cols, ctx) -> float     measured condition in the untouched data
  apply(df, rows, cols, value, rng, ctx) -> df     returns a modified COPY; only `rows` change
  ladder: "relative" (Nx of measured base) or "absolute" (base is 0 by definition)
  requires: profile fields that must be confirmed before use
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd


@dataclass
class Injector:
    name: str
    description: str
    ladder: str
    limit_key: str | None
    base_condition: Callable[..., float]
    apply: Callable[..., pd.DataFrame]
    requires: list[str] = field(default_factory=list)
    numeric_only: bool = False


def _robust_z(x: pd.Series) -> pd.Series:
    med = x.median()
    mad = (x - med).abs().median() * 1.4826
    scale = mad if mad and mad > 0 else x.std()
    if not scale or scale == 0 or np.isnan(scale):
        return pd.Series(0.0, index=x.index)
    return (x - med).abs() / scale


# ---- missing ---------------------------------------------------------------
def _missing_base(df, rows, cols, ctx) -> float:
    return float(df.loc[rows, cols].isna().to_numpy().mean())


def _missing_apply(df, rows, cols, value, rng, ctx) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        sub = out.loc[rows, c]
        r = float(sub.isna().mean())
        if value <= r:
            continue
        p_add = (value - r) / (1 - r) if r < 1 else 0.0
        present = sub.index[sub.notna()]
        k = int(round(p_add * len(present)))
        if k > 0:
            pick = rng.choice(len(present), size=k, replace=False)
            if pd.api.types.is_integer_dtype(out[c]) or pd.api.types.is_bool_dtype(out[c]):
                out[c] = out[c].astype("float64") if pd.api.types.is_integer_dtype(out[c]) else out[c].astype("object")
            out.loc[present[pick], c] = np.nan
    return out


# ---- outliers --------------------------------------------------------------
def _outlier_base(df, rows, cols, ctx) -> float:
    z = ctx.get("amp", {}).get("outliers", {}).get("detection_z_mad", 5.0)
    shares = [float((_robust_z(df.loc[rows, c].astype(float)) > z).mean()) for c in cols]
    return float(np.mean(shares)) if shares else 0.0


def _outlier_apply(df, rows, cols, value, rng, ctx) -> pd.DataFrame:
    cfg = ctx.get("amp", {}).get("outliers", {})
    zthr, mag = cfg.get("detection_z_mad", 5.0), cfg.get("injection_magnitude_mad", 10.0)
    out = df.copy()
    for c in cols:
        out[c] = out[c].astype("float64")
        sub = out.loc[rows, c]
        z = _robust_z(sub)
        cur = float((z > zthr).mean())
        k = int(round(max(0.0, value - cur) * len(sub)))
        cand = sub.index[(z <= zthr) & sub.notna()]
        if k <= 0 or len(cand) == 0:
            continue
        k = min(k, len(cand))
        pick = cand[rng.choice(len(cand), size=k, replace=False)]
        med = sub.median()
        mad = (sub - med).abs().median() * 1.4826
        scale = mad if mad and mad > 0 else (sub.std() or 1.0)
        nonneg = bool((sub.dropna() >= 0).all())
        signs = np.ones(k) if nonneg else rng.choice([-1.0, 1.0], size=k)
        out.loc[pick, c] = med + signs * mag * scale * (1 + rng.random(k))
    return out


# ---- distribution shift ----------------------------------------------------
def _zero(df, rows, cols, ctx) -> float:
    return 0.0


def _shift_apply(df, rows, cols, value, rng, ctx) -> pd.DataFrame:
    kind = ctx.get("params", {}).get("kind", "additive")
    out = df.copy()
    for c in cols:
        out[c] = out[c].astype("float64")
        ref = out.loc[ctx["train_rows"], c]
        if kind == "multiplicative":
            out.loc[rows, c] = out.loc[rows, c] * (1 + value)
        else:
            out.loc[rows, c] = out.loc[rows, c] + value * float(ref.std() or 0.0)
    return out


# ---- timing: stale features ------------------------------------------------
def _lag_apply(df, rows, cols, value, rng, ctx) -> pd.DataFrame:
    k = int(value)
    tcol, keys = ctx["profile"]["time_column"], list(ctx["profile"].get("entity_keys") or [])
    out = df.copy()
    order = out.assign(__t=pd.to_datetime(out[tcol], errors="coerce", format="mixed")) \
               .sort_values([*keys, "__t"]).index
    s = out.loc[order]
    if keys:
        lagged = s.groupby(keys, sort=False)[cols].shift(k)
        lagged = lagged.fillna(s.groupby(keys, sort=False)[cols].transform("first"))
    else:
        lagged = s[cols].shift(k).fillna(s[cols].iloc[0])
    for c in cols:
        out.loc[rows, c] = lagged.loc[rows, c].to_numpy()
    return out


INJECTORS: dict[str, Injector] = {
    "missing": Injector("missing", "Raise the share of missing cells in selected columns (MCAR).",
                        "relative", "missing_rate_max", _missing_base, _missing_apply),
    "outliers": Injector("outliers", "Raise the share of extreme values (robust-z) in numeric columns.",
                         "relative", "outlier_fraction_max", _outlier_base, _outlier_apply, numeric_only=True),
    "shift": Injector("shift", "Shift the distribution of numeric columns by k std (or x(1+k) multiplicative).",
                      "absolute", "shift_std_max", _zero, _shift_apply, numeric_only=True),
    "time_lag": Injector("time_lag", "Make features stale: value from k periods earlier within each entity.",
                         "absolute", None, _zero, _lag_apply, requires=["time_column", "entity_keys"]),
}


def neutralize(df: pd.DataFrame, rows, col: str, train_rows) -> pd.DataFrame:
    """Feature ablation: replace a feature with a constant learned on train rows."""
    out = df.copy()
    ref = out.loc[train_rows, col]
    if pd.api.types.is_numeric_dtype(ref):
        fill: Any = float(ref.median())
        out[col] = out[col].astype("float64")
    else:
        fill = ref.mode().iloc[0] if not ref.mode().empty else None
    out.loc[rows, col] = fill
    return out


def build_levels(inj: Injector, base: float, amp: dict[str, Any], override: list[float] | None = None) -> tuple[list[dict], str]:
    limits = amp.get("limits", {})
    limit = float(limits.get(inj.limit_key, np.inf)) if inj.limit_key else np.inf
    levels = [{"label": "1x", "condition": base, "inject": False, "limit_exceeded": False}]
    if override:
        for i, v in enumerate(override, 1):
            levels.append({"label": f"A{i}", "condition": min(v, limit), "requested": v,
                           "inject": True, "limit_exceeded": v > limit})
        return levels, "absolute ladder (explicit levels from spec)"
    if inj.ladder == "relative" and base > 0:
        for m in amp.get("severity_multipliers", [1, 2, 3, 5]):
            if m == 1:
                continue
            v = m * base
            levels.append({"label": f"{m}x", "multiplier": m, "condition": min(v, limit), "requested": v,
                           "inject": True, "limit_exceeded": v > limit})
        return levels, f"relative ladder: condition = N x measured base ({base:.4g})"
    vals = amp.get("absolute_ladders", {}).get(inj.name, [])
    for i, v in enumerate(vals, 1):
        levels.append({"label": f"A{i}", "condition": min(v, limit), "requested": v,
                       "inject": True, "limit_exceeded": v > limit})
    why = "base condition is 0" if inj.ladder == "relative" else "condition has no natural base"
    return levels, f"absolute ladder ({why}); levels are NOT multiples of the base"
