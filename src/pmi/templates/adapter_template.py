"""PMI adapter — the bridge between the harness and the investigated project.

Rules (enforced by guard hook + harness):
  * Written by the agent ONLY here: runs/<run_id>/workspace/pmi_adapter.py
  * Reads the project from the isolated copy in ./target — never from the original folder.
  * Must MIRROR the project's own pipeline (data loading, split / evaluation protocol,
    preprocessing, model). It is not a place to "improve" the project.
  * Every choice below must cite where it comes from in the project (file:line).
  * Fidelity is proven by `pmi baseline` reproducing the project's reported metric,
    or confirmed by the human with `pmi adapter confirm`.

Contract (checked by `pmi adapter validate`):
  target: str                       -> target column name in load_data() output
  load_data() -> pandas.DataFrame   -> one row per prediction unit, includes target column
  split(df) -> (train_index, test_index)
                                    -> index LABELS of df (no reset_index), disjoint,
                                       mirroring the project's evaluation protocol
  fit(train_df, seed=0) -> model    -> train exactly as the project does
  predict(model, df) -> 1-D array   -> point predictions (or class labels) for df rows
  predict_proba(model, df) -> array -> OPTIONAL, positive-class probability (classification)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

TARGET_ROOT = Path(__file__).resolve().parent / "target"   # isolated copy of the project
sys.path.insert(0, str(TARGET_ROOT))                         # lets you import project modules


class Adapter:
    # Source citation for each decision, e.g. "train.py:42 y = df['col']"
    sources: dict[str, str] = {
        "target": "TODO file:line",
        "load_data": "TODO file:line",
        "split": "TODO file:line",
        "fit": "TODO file:line",
        "predict": "TODO file:line",
    }
    target: str = "TODO"

    def load_data(self) -> pd.DataFrame:
        raise NotImplementedError("Mirror the project's data loading here.")

    def split(self, df: pd.DataFrame):
        raise NotImplementedError("Return (train_index, test_index) exactly as the project evaluates.")

    def fit(self, train_df: pd.DataFrame, seed: int = 0):
        raise NotImplementedError("Train exactly as the project does.")

    def predict(self, model, df: pd.DataFrame):
        raise NotImplementedError("Return predictions for df rows.")
