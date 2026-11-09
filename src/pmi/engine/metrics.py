"""Metrics. Two implementations on purpose:

* `compute`        — primary (numpy), used by experiments
* `recompute`      — independent path (sklearn / pandas formulas), used by `pmi verify`
                     to re-derive every recorded number from saved predictions.

No metric is "the" metric: the profile's confirmed `primary_metric` decides what is reported.
"""
from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
import pandas as pd

ALIASES = {
    "mean_absolute_error": "mae", "mean_squared_error": "mse", "root_mean_squared_error": "rmse",
    "r2_score": "r2", "accuracy_score": "accuracy", "f1_score": "f1", "roc_auc_score": "roc_auc",
    "mean_absolute_percentage_error": "mape", "balanced_accuracy_score": "balanced_accuracy",
    "log_loss": "log_loss", "median_absolute_error": "medae",
}
HIGHER_IS_BETTER = {"r2", "accuracy", "f1", "balanced_accuracy", "roc_auc"}
SIGNED = {"bias", "mean_error"}
NEEDS_PROBA = {"roc_auc", "log_loss"}
REGRESSION = ["mae", "rmse", "mse", "wape", "bias", "mean_error", "smape", "mape", "mape_nonzero", "medae", "r2"]
CLASSIFICATION = ["accuracy", "error_rate", "f1", "balanced_accuracy", "roc_auc", "log_loss"]


def canonical_name(name: str) -> str:
    n = (name or "").strip().lower()
    return ALIASES.get(n, n)


def _f(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return y, p, p - y


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b not in (0, 0.0) else float("nan")


def _mae(y, p, _=None):
    y, p, e = _f(y, p); return float(np.mean(np.abs(e)))
def _mse(y, p, _=None):
    y, p, e = _f(y, p); return float(np.mean(e ** 2))
def _rmse(y, p, _=None):
    return math.sqrt(_mse(y, p))
def _medae(y, p, _=None):
    y, p, e = _f(y, p); return float(np.median(np.abs(e)))
def _wape(y, p, _=None):
    y, p, e = _f(y, p); return _safe_div(np.sum(np.abs(e)), np.sum(np.abs(y)))
def _bias(y, p, _=None):
    y, p, e = _f(y, p); return _safe_div(np.sum(e), np.sum(np.abs(y)))
def _mean_error(y, p, _=None):
    y, p, e = _f(y, p); return float(np.mean(e))
def _smape(y, p, _=None):
    y, p, e = _f(y, p)
    den = np.abs(y) + np.abs(p)
    r = np.where(den == 0, 0.0, 2 * np.abs(e) / np.where(den == 0, 1, den))
    return float(np.mean(r))
def _mape(y, p, _=None):
    y, p, e = _f(y, p); return float(np.mean(np.abs(e) / np.maximum(np.abs(y), np.finfo(float).eps)))
def _mape_nonzero(y, p, _=None):
    y, p, e = _f(y, p); m = y != 0
    return float(np.mean(np.abs(e[m]) / np.abs(y[m]))) if m.any() else float("nan")
def _r2(y, p, _=None):
    y, p, e = _f(y, p); ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum(e ** 2) / ss) if ss > 0 else float("nan")
def _acc(y, p, _=None):
    return float(np.mean(np.asarray(y) == np.asarray(p)))
def _err(y, p, _=None):
    return 1.0 - _acc(y, p)
def _f1(y, p, _=None):
    y, p = np.asarray(y), np.asarray(p)
    labels = np.unique(np.concatenate([y, p]))
    scores = []
    for c in labels:
        tp = np.sum((p == c) & (y == c)); fp = np.sum((p == c) & (y != c)); fn = np.sum((p != c) & (y == c))
        scores.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    if len(labels) == 2:   # binary: positive = larger label (sklearn default pos_label=1 for {0,1})
        return float(scores[-1])
    return float(np.mean(scores))
def _bal_acc(y, p, _=None):
    y, p = np.asarray(y), np.asarray(p)
    return float(np.mean([np.mean(p[y == c] == c) for c in np.unique(y)]))
def _auc(y, p, proba=None):
    if proba is None:
        return float("nan")
    y = np.asarray(y); s = np.asarray(proba, dtype=float)
    pos = y == np.max(y)
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    ranks = pd.Series(s).rank().to_numpy()
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
def _logloss(y, p, proba=None):
    if proba is None:
        return float("nan")
    y = (np.asarray(y) == np.max(y)).astype(float)
    q = np.clip(np.asarray(proba, dtype=float), 1e-15, 1 - 1e-15)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


PRIMARY: dict[str, Callable[..., float]] = {
    "mae": _mae, "mse": _mse, "rmse": _rmse, "medae": _medae, "wape": _wape, "bias": _bias,
    "mean_error": _mean_error, "smape": _smape, "mape": _mape, "mape_nonzero": _mape_nonzero, "r2": _r2,
    "accuracy": _acc, "error_rate": _err, "f1": _f1, "balanced_accuracy": _bal_acc,
    "roc_auc": _auc, "log_loss": _logloss,
}


def available(task_type: str | None) -> list[str]:
    t = (task_type or "").lower()
    return CLASSIFICATION if t == "classification" else REGRESSION


def compute(names: list[str], y, p, proba=None) -> dict[str, float]:
    out = {}
    for n in names:
        c = canonical_name(n)
        if c not in PRIMARY:
            raise KeyError(f"Unknown metric '{n}'. Known: {sorted(PRIMARY)}")
        if c in NEEDS_PROBA and proba is None:
            continue
        out[c] = PRIMARY[c](y, p, proba)
    return out


def as_loss(name: str, value: float) -> float:
    """Monotone 'badness' used for amplification factors."""
    c = canonical_name(name)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    if c in HIGHER_IS_BETTER:
        return 1.0 - value
    if c in SIGNED:
        return abs(value)
    return value


# ---------------------------------------------------------------------------
# Independent recomputation (different code path) for verification
# ---------------------------------------------------------------------------
def recompute(name: str, y, p, proba=None) -> float:
    from sklearn import metrics as skm
    c = canonical_name(name)
    ys, ps = pd.Series(y).reset_index(drop=True), pd.Series(p).reset_index(drop=True)
    if c == "mae":
        return float(skm.mean_absolute_error(ys, ps))
    if c == "mse":
        return float(skm.mean_squared_error(ys, ps))
    if c == "rmse":
        return float(math.sqrt(skm.mean_squared_error(ys, ps)))
    if c == "medae":
        return float(skm.median_absolute_error(ys, ps))
    if c == "r2":
        return float(skm.r2_score(ys, ps)) if ys.nunique() > 1 else float("nan")
    if c == "mape":
        return float(skm.mean_absolute_percentage_error(ys, ps))
    if c == "wape":
        d = ys.abs().sum()
        return float((ps - ys).abs().sum() / d) if d else float("nan")
    if c == "bias":
        d = ys.abs().sum()
        return float((ps - ys).sum() / d) if d else float("nan")
    if c == "mean_error":
        return float((ps - ys).mean())
    if c == "smape":
        den = ys.abs() + ps.abs()
        terms = (2 * (ps - ys).abs() / den.where(den != 0)).fillna(0.0)
        return float(terms.mean())
    if c == "mape_nonzero":
        m = ys != 0
        return float(((ps[m] - ys[m]).abs() / ys[m].abs()).mean()) if m.any() else float("nan")
    if c == "accuracy":
        return float(skm.accuracy_score(ys, ps))
    if c == "error_rate":
        return float(1 - skm.accuracy_score(ys, ps))
    if c == "f1":
        avg = "binary" if pd.concat([ys, ps]).nunique() == 2 else "macro"
        kw: dict[str, Any] = {"average": avg}
        if avg == "binary":
            kw["pos_label"] = max(pd.concat([ys, ps]).unique())
        return float(skm.f1_score(ys, ps, **kw))
    if c == "balanced_accuracy":
        return float(skm.balanced_accuracy_score(ys, ps))
    if c == "roc_auc":
        return float(skm.roc_auc_score(ys == ys.max(), proba)) if proba is not None else float("nan")
    if c == "log_loss":
        return float(skm.log_loss(ys == ys.max(), proba, labels=[False, True])) if proba is not None else float("nan")
    raise KeyError(c)
