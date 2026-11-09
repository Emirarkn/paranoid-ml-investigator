"""Adapter loading + validation. Runs INSIDE the worker subprocess only."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pmi.profiling.loaders import load_table


class AdapterError(RuntimeError):
    pass


def load_project_adapter(path: Path):
    if not path.is_file():
        raise AdapterError(f"Adapter file missing: {path}")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("pmi_adapter", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    if not hasattr(mod, "Adapter"):
        raise AdapterError("pmi_adapter.py must define class Adapter")
    return mod.Adapter()


class SurrogateAdapter:
    """Stand-in model when the project has no runnable pipeline.

    Results produced with it describe the SURROGATE, not the project: evidence is capped at
    `Simulated`. Note: HistGradientBoosting handles NaN natively, so missing-data robustness
    of the surrogate says little about the project's own model.
    """

    sources = {"all": "pmi surrogate (not the project's model)"}

    def __init__(self, cfg: dict[str, Any], workspace: Path):
        self.cfg = cfg
        self.workspace = workspace
        self.target = cfg["target"]
        self.features = list(cfg["features"])
        self.task_type = cfg.get("task_type", "regression")

    def load_data(self) -> pd.DataFrame:
        return load_table(self.workspace / "target" / self.cfg["data_source"])

    def split(self, df: pd.DataFrame):
        sp = self.cfg.get("split", {"kind": "random", "test_fraction": 0.2})
        frac = float(sp.get("test_fraction", 0.2))
        if sp.get("kind") == "temporal":
            t = pd.to_datetime(df[sp["time_column"]], errors="coerce", format="mixed")
            cut = t.quantile(1 - frac)
            return df.index[t <= cut], df.index[t > cut]
        rng = np.random.default_rng(int(sp.get("seed", 0)))
        mask = rng.random(len(df)) < frac
        return df.index[~mask], df.index[mask]

    def _X(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.features].copy()
        for c in X.columns:
            if not pd.api.types.is_numeric_dtype(X[c]):
                X[c] = X[c].astype("category").cat.codes.replace(-1, np.nan)
        return X

    def fit(self, train_df: pd.DataFrame, seed: int = 0):
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
        cls = HistGradientBoostingClassifier if self.task_type == "classification" else HistGradientBoostingRegressor
        m = cls(random_state=seed, max_iter=200)
        m.fit(self._X(train_df), train_df[self.target])
        return m

    def predict(self, model, df: pd.DataFrame):
        return model.predict(self._X(df))

    def predict_proba(self, model, df: pd.DataFrame):
        if self.task_type != "classification":
            raise AttributeError
        return model.predict_proba(self._X(df))[:, -1]


def get_adapter(job: dict[str, Any]):
    meta = job.get("adapter") or {}
    ws = Path(job["workspace"])
    if meta.get("kind") == "surrogate":
        return SurrogateAdapter(meta["config"], ws)
    return load_project_adapter(ws / "pmi_adapter.py")


def split_indices(adapter, df: pd.DataFrame):
    tr, te = adapter.split(df)
    tr, te = pd.Index(tr), pd.Index(te)
    if not tr.isin(df.index).all() or not te.isin(df.index).all():
        raise AdapterError("split() must return index LABELS of the dataframe from load_data() (no reset_index).")
    if len(tr) == 0 or len(te) == 0:
        raise AdapterError("split() returned an empty train or test set.")
    if len(tr.intersection(te)):
        raise AdapterError("split() train and test indices overlap.")
    return tr, te


def predict(adapter, model, df: pd.DataFrame):
    p = np.asarray(adapter.predict(model, df)).reshape(-1)
    if len(p) != len(df):
        raise AdapterError(f"predict() returned {len(p)} values for {len(df)} rows.")
    proba = None
    if hasattr(adapter, "predict_proba"):
        try:
            proba = np.asarray(adapter.predict_proba(model, df)).reshape(-1)
        except (AttributeError, NotImplementedError):
            proba = None
    return p, proba


def validate(adapter) -> dict[str, Any]:
    out: dict[str, Any] = {"checks": []}

    def ok(name, cond, detail=""):
        out["checks"].append({"check": name, "ok": bool(cond), "detail": detail})
        if not cond:
            raise AdapterError(f"{name}: {detail}")

    tgt = getattr(adapter, "target", None)
    ok("target attribute", isinstance(tgt, str) and tgt and tgt != "TODO", f"target={tgt!r}")
    df = adapter.load_data()
    ok("load_data returns DataFrame", isinstance(df, pd.DataFrame), type(df).__name__)
    ok("target column present", tgt in df.columns, f"columns: {list(df.columns)[:30]}")
    ok("index unique", df.index.is_unique, "load_data() index must be unique")
    tr, te = split_indices(adapter, df)
    out.update({"n_rows": len(df), "n_train": len(tr), "n_test": len(te), "target": tgt,
                "columns": [str(c) for c in df.columns]})
    model = adapter.fit(df.loc[tr], seed=0)
    p, proba = predict(adapter, model, df.loc[te])
    ok("predictions finite", np.isfinite(pd.to_numeric(pd.Series(p), errors="coerce")).mean() > 0.99
       or not pd.api.types.is_numeric_dtype(pd.Series(p)), "predict() returned non-finite values")
    out["has_proba"] = proba is not None
    out["sources"] = getattr(adapter, "sources", {})
    todo = [k for k, v in out["sources"].items() if "TODO" in str(v)]
    out["missing_source_citations"] = todo
    return out
