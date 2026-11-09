from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from pmi.cli import main

REPO = Path(__file__).resolve().parents[1]


def _load_examples():
    spec = importlib.util.spec_from_file_location("make_examples", REPO / "examples" / "make_examples.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def projects(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("projects")
    _load_examples().main(str(out))
    return out


@pytest.fixture()
def harness(tmp_path, monkeypatch) -> Path:
    h = tmp_path / "harness"
    shutil.copytree(REPO / "config", h / "config")
    (h / "runs").mkdir()
    monkeypatch.setenv("PMI_HOME", str(h))
    return h


@pytest.fixture()
def pmi(capsys):
    """Call the CLI in-process; return (exit_code, parsed_json_or_text)."""
    def _call(*args: str):
        capsys.readouterr()
        rc = main(list(args))
        out = capsys.readouterr()
        try:
            return rc, json.loads(out.out)
        except json.JSONDecodeError:
            return rc, out.out + out.err
    return _call


RETAIL_ADAPTER = '''
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
TARGET_ROOT = Path(__file__).resolve().parent / "target"
FEATURES = ["promo_flag", "price", "temp_c", "units_lag1", "units_next_wk"]
class Adapter:
    sources = {"target": "train.py:11", "load_data": "train.py:7", "split": "train.py:15",
               "fit": "train.py:17", "predict": "train.py:19"}
    target = "units_sold"
    def load_data(self):
        return pd.read_csv(TARGET_ROOT / "data" / "store_week.csv")
    def split(self, df):
        return train_test_split(df.index, test_size=0.2, random_state=42)
    def fit(self, train_df, seed=0):
        return RandomForestRegressor(n_estimators=60, random_state=42 + seed).fit(train_df[FEATURES], train_df[self.target])
    def predict(self, model, df):
        return model.predict(df[FEATURES])
'''

CHURN_ADAPTER = '''
from pathlib import Path
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
TARGET_ROOT = Path(__file__).resolve().parent / "target"
COLS = ["tenure_m", "monthly_fee", "n_tickets"]
class Adapter:
    sources = {"target": "model.py:10", "load_data": "model.py:9", "split": "model.py:13",
               "fit": "model.py:14", "predict": "model.py:16"}
    target = "churned"
    def load_data(self):
        return pd.read_csv(TARGET_ROOT / "data" / "customers.csv")
    def split(self, df):
        return train_test_split(df.index, test_size=0.25, random_state=7, stratify=df[self.target])
    def fit(self, train_df, seed=0):
        clf = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500))
        return clf.fit(train_df[COLS], train_df[self.target])
    def predict(self, model, df):
        return model.predict(df[COLS])
    def predict_proba(self, model, df):
        return model.predict_proba(df[COLS])[:, 1]
'''
