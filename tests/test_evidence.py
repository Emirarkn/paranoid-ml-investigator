"""Stage 3 acceptance: Suspected / Verified / Rejected never mix; evidence is tamper-evident."""
from __future__ import annotations

import sqlite3

from tests.conftest import RETAIL_ADAPTER


def _setup_retail(harness, projects, pmi, confirm_reported=True):
    rc, out = pmi("init", "--target", str(projects / "retail_weekly"))
    run_dir = harness / "runs" / out["run_id"]
    pmi("scan")
    for f, v, e in [("target", "units_sold", "train.py:11"), ("task_type", "regression", "train.py:17"),
                    ("time_column", "week_start", "scan"), ("entity_keys", '["store_code"]', "scan"),
                    ("data_source", "data/store_week.csv", "train.py:7"), ("primary_metric", "mae", "train.py:19")]:
        assert pmi("profile", "set", f, v, "--evidence", e)[0] == 0
    (run_dir / "workspace" / "pmi_adapter.py").write_text(RETAIL_ADAPTER, encoding="utf-8")
    return run_dir


def _hyp(pmi, title="h", kind="defect"):
    rc, out = pmi("hypothesis", "add", "--title", title, "--statement", "statement long enough",
                  "--mechanism", "mechanism long enough", "--falsification", "falsification long enough",
                  "--kind", kind)
    assert rc == 0 and out["status"] == "Suspected"
    return out["id"]


def test_verify_requires_experiment(harness, projects, pmi):
    _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    rc, msg = pmi("verify", hid)
    assert rc == 2 and "stays Suspected" in msg


def test_preregistration_required(harness, projects, pmi):
    _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    rc, msg = pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
                  "--spec", '{"check":"target_proxy"}', "--rule", '{"type":"eaf"}')
    assert rc == 2 and "pre-registration" in msg


def test_future_leak_verified_and_decoy_not_flagged(harness, projects, pmi):
    _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi, "future leak")
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"target_proxy","data_via":"profile"}', "--rule", '{"type":"defect_found"}')
    rc, e = pmi("experiment", "run", "E-001")
    flagged = {f["column"] for f in e["result"]["observed"]["flagged"]}
    assert flagged == {"units_next_wk"}          # units_lag1 is a legitimate past value (decoy)
    rc, v = pmi("verify", hid)
    assert v["status"] == "Verified"


def test_adapter_split_check_needs_fidelity(harness, projects, pmi):
    _setup_retail(harness, projects, pmi)
    assert pmi("adapter", "validate")[0] == 0
    hid = _hyp(pmi, "random split")
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"temporal_overlap"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-001")
    rc, v = pmi("verify", hid)
    assert v["status"] == "Inconclusive" and "fidelity" in v["reason"]
    # reproduce the project's own number -> adapter fidelity confirmed -> a new check can verify
    pmi("profile", "set", "reported_metric", '{"metric":"mae","value":4.3044}', "--evidence", "train.py output")
    rc, b = pmi("baseline")
    assert b["adapter_fidelity_now"] == "confirmed"
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"temporal_overlap"}', "--rule", '{"type":"defect_found"}')
    eid = [e for e in pmi("experiment", "list")[1] if e["hypothesis_id"] == hid][-1]["id"]
    pmi("experiment", "run", eid)
    rc, v = pmi("verify", hid)
    # first experiment ran under unconfirmed fidelity (inconclusive), second passes -> Verified
    assert v["status"] == "Verified"


def test_ledger_tampering_detected(harness, projects, pmi):
    run_dir = _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    con = sqlite3.connect(run_dir / "ledger.sqlite")
    con.execute("UPDATE hypotheses SET status='Verified' WHERE id=?", (hid,))
    con.commit()
    con.close()
    rc, integ = pmi("integrity")
    assert rc == 3 and not integ["ledger_chain"]["ok"]


def test_artifact_tampering_blocks_verification(harness, projects, pmi):
    run_dir = _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"target_proxy","data_via":"profile"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-001")
    (run_dir / "artifacts" / "E-001" / "check_result.json").write_text("{}", encoding="utf-8")
    rc, v = pmi("verify", hid)
    assert v["status"] == "Inconclusive" and "changed after the experiment" in v["reason"]


def test_experiment_runs_only_once(harness, projects, pmi):
    _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"target_proxy","data_via":"profile"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-001")
    rc, msg = pmi("experiment", "run", "E-001")
    assert rc == 2 and "run once" in msg
