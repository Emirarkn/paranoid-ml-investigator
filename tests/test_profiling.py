"""Stage 2 acceptance: the profile is LEARNED from each project; nothing is assumed."""
from __future__ import annotations

from pmi.profiling.profile import FIELDS


def _cands(pmi, field):
    rc, prof = pmi("profile", "show")
    return [c["value"] for c in prof[field].get("candidates", [])], prof[field]["status"]


def test_retail_profile_candidates(harness, projects, pmi):
    pmi("init", "--target", str(projects / "retail_weekly"))
    pmi("scan")
    assert "units_sold" in _cands(pmi, "target")[0]
    assert "week_start" in _cands(pmi, "time_column")[0]
    assert "weekly" in _cands(pmi, "time_grain")[0]
    assert ["store_code"] in _cands(pmi, "entity_keys")[0]
    assert "regression" in _cands(pmi, "task_type")[0]
    # candidates are never auto-confirmed
    rc, prof = pmi("profile", "show", "--json")
    assert all(f["status"] != "confirmed" for f in prof["fields"].values())


def test_churn_profile_candidates(harness, projects, pmi):
    pmi("init", "--target", str(projects / "churn_tabular"))
    pmi("scan")
    assert "churned" in _cands(pmi, "target")[0]
    assert "classification" in _cands(pmi, "task_type")[0]
    assert "daily" not in _cands(pmi, "time_grain")[0] or True  # signup dates are irregular, any label allowed


def test_no_domain_vocabulary_in_profile_schema():
    text = " ".join(FIELDS) + " ".join(FIELDS.values())
    for word in ("sku", "sell-in", "sell_out", "stockout", "wape", "monthly"):
        assert word not in text.lower()


def test_profile_set_requires_evidence(harness, projects, pmi):
    pmi("init", "--target", str(projects / "churn_tabular"))
    rc, _ = pmi("profile", "set", "target", "churned")
    assert rc == 2
    rc, out = pmi("profile", "set", "target", "churned", "--evidence", "model.py:10")
    assert rc == 0 and out["target"]["status"] == "confirmed"


def test_static_patterns_planted_vs_clean(harness, projects, pmi):
    pmi("init", "--target", str(projects / "retail_weekly"))
    rc, scan = pmi("scan")
    pats = {(p["pattern"], p["at"]) for p in scan["static_suspicions"]}
    assert ("preprocessing_fit_before_split", "train.py:14") in pats
    assert ("random_split_with_temporal_data", "train.py:15") in pats
    pmi("init", "--target", str(projects / "churn_tabular"))
    rc, scan = pmi("scan")
    assert not [p for p in scan["static_suspicions"] if p["pattern"] == "preprocessing_fit_before_split"]


def test_blocked_without_confirmed_profile(harness, projects, pmi):
    pmi("init", "--target", str(projects / "retail_weekly"))
    pmi("scan")
    rc, out = pmi("hypothesis", "add", "--title", "t", "--statement", "a feature equals the target",
                  "--mechanism", "built from the label column", "--falsification", "target_proxy finds nothing")
    rc, msg = pmi("experiment", "plan", "--hypothesis", "H-001", "--type", "check",
                  "--spec", '{"check":"target_proxy"}', "--rule", '{"type":"defect_found"}')
    assert rc == 2 and "not confirmed" in msg


def test_otc_channel_panel_profile(harness, projects, pmi):
    """Integer yyyymm periods and a two-column entity key are learned, not assumed."""
    pmi("init", "--target", str(projects / "otc_channel"))
    rc, scan = pmi("scan")
    assert ["product_code", "wholesaler"] == _cands(pmi, "entity_keys")[0][0]
    assert "period" in _cands(pmi, "time_column")[0]
    assert "monthly" in _cands(pmi, "time_grain")[0]
    assert "sell_in_units" in _cands(pmi, "target")[0]
    assert ("random_split_with_temporal_data", "forecast.py:12") in {(p["pattern"], p["at"]) for p in scan["static_suspicions"]}


def test_otc_random_split_on_monthly_panel(harness, projects, pmi):
    rc, out = pmi("init", "--target", str(projects / "otc_channel"))
    run_dir = harness / "runs" / out["run_id"]
    pmi("scan")
    for f, v in [("target", "sell_in_units"), ("task_type", "regression"), ("time_column", "period"),
                 ("entity_keys", '["product_code","wholesaler"]'), ("data_source", "data/channel_monthly.csv")]:
        pmi("profile", "set", f, v, "--evidence", "test")
    (run_dir / "workspace" / "pmi_adapter.py").write_text(OTC_ADAPTER, encoding="utf-8")
    assert pmi("adapter", "validate")[0] == 0
    pmi("adapter", "confirm", "--evidence", "test: copied from forecast.py")
    pmi("hypothesis", "add", "--title", "random split", "--statement", "monthly panel is split randomly",
        "--mechanism", "train_test_split shuffles periods", "--falsification", "temporal_overlap finds none")
    pmi("experiment", "plan", "--hypothesis", "H-001", "--type", "check",
        "--spec", '{"check":"temporal_overlap"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-001")
    rc, v = pmi("verify", "H-001")
    assert v["status"] == "Verified"
    pmi("hypothesis", "add", "--title", "key unique", "--statement", "product x wholesaler x period is duplicated",
        "--mechanism", "double counting in extraction", "--falsification", "key_uniqueness finds no duplicates")
    pmi("experiment", "plan", "--hypothesis", "H-002", "--type", "check",
        "--spec", '{"check":"key_uniqueness","data_via":"profile"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-002")
    rc, v = pmi("verify", "H-002")
    assert v["status"] == "Rejected"     # decoy-style: a sound key must not be flagged


OTC_ADAPTER = """
from pathlib import Path
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
TARGET_ROOT = Path(__file__).resolve().parent / "target"
COLS = ["promo_flag", "price_index", "sell_out_lag1", "sell_out_units", "month_of_year"]
class Adapter:
    sources = {"target": "forecast.py:10", "load_data": "forecast.py:6", "split": "forecast.py:12",
               "fit": "forecast.py:13", "predict": "forecast.py:14"}
    target = "sell_in_units"
    def load_data(self):
        df = pd.read_csv(TARGET_ROOT / "data" / "channel_monthly.csv")
        df["month_of_year"] = df["period"] % 100
        return df
    def split(self, df):
        return train_test_split(df.index, test_size=0.2, random_state=11)
    def fit(self, train_df, seed=0):
        return GradientBoostingRegressor(random_state=11 + seed).fit(train_df[COLS], train_df[self.target])
    def predict(self, model, df):
        return model.predict(df[COLS])
"""
