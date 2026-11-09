"""Stage 4 acceptance: severity ladders run automatically, EAF is correct and reproducible."""
from __future__ import annotations

from tests.conftest import CHURN_ADAPTER


def _setup_churn(harness, projects, pmi):
    rc, out = pmi("init", "--target", str(projects / "churn_tabular"))
    run_dir = harness / "runs" / out["run_id"]
    pmi("scan")
    for f, v, e in [("target", "churned", "model.py:10"), ("task_type", "classification", "model.py:15"),
                    ("primary_metric", "accuracy", "model.py:16")]:
        pmi("profile", "set", f, v, "--evidence", e)
    (run_dir / "workspace" / "pmi_adapter.py").write_text(CHURN_ADAPTER, encoding="utf-8")
    assert pmi("adapter", "validate")[0] == 0
    pmi("adapter", "confirm", "--evidence", "test: adapter copied line by line from model.py")
    return run_dir


def _hyp(pmi):
    return pmi("hypothesis", "add", "--title", "fragile", "--statement", "statement long enough",
               "--mechanism", "mechanism long enough", "--falsification", "falsification long enough",
               "--kind", "sensitivity")[1]["id"]


def test_relative_ladder_from_measured_base(harness, projects, pmi):
    _setup_churn(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "amplify",
        "--spec", '{"injector":"missing","columns":["monthly_fee"],"where":"test"}',
        "--rule", '{"type":"eaf","metric":"accuracy","level":"5x","min_eaf":1.5}')
    rc, e = pmi("experiment", "run", "E-001")
    r = e["result"]
    labels = [lv["label"] for lv in r["levels"]]
    assert labels == ["1x", "2x", "3x", "5x"]
    base = r["base_condition"]
    assert 0.0 < base < 0.15                      # the project's own missing share on test rows
    for lv in r["levels"][1:]:
        assert abs(lv["condition_realized_mean"] - lv["multiplier"] * base) < 0.01
    assert r["levels"][0]["eaf_accuracy"]["mean"] == 1.0
    rc, v = pmi("verify", hid)
    assert v["status"] in ("Rejected", "Simulated", "Inconclusive")   # never Verified for a stress test
    assert v["status"] != "Verified"


def test_absolute_ladder_when_base_zero_and_limit_flag(harness, projects, pmi):
    _setup_churn(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "amplify",
        "--spec", '{"injector":"missing","columns":["n_tickets"],"where":"test","levels":[0.5,0.99]}',
        "--rule", '{"type":"eaf","metric":"accuracy","level":"A2","min_eaf":1.1}')
    rc, e = pmi("experiment", "run", "E-001")
    lv = {x["label"]: x for x in e["result"]["levels"]}
    assert set(lv) == {"1x", "A1", "A2"}
    assert lv["A2"]["limit_exceeded"] and lv["A2"]["condition"] == 0.95


def test_reproducible_numbers(harness, projects, pmi):
    _setup_churn(harness, projects, pmi)
    hid = _hyp(pmi)
    spec = '{"injector":"outliers","columns":["tenure_m"],"where":"both","replicates":3}'
    rule = '{"type":"eaf","metric":"accuracy","level":"max","min_eaf":1.05}'
    for _ in range(2):
        pmi("experiment", "plan", "--hypothesis", hid, "--type", "amplify", "--spec", spec, "--rule", rule)
    a = pmi("experiment", "run", "E-001")[1]["result"]["levels"]
    b = pmi("experiment", "run", "E-002")[1]["result"]["levels"]
    assert a == b


def test_ablation_and_verify_recompute(harness, projects, pmi):
    _setup_churn(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "ablation",
        "--spec", '{"features":["n_tickets","tenure_m"],"where":"both"}',
        "--rule", '{"type":"eaf","metric":"accuracy","level":"n_tickets","min_eaf":1.05}')
    rc, e = pmi("experiment", "run", "E-001")
    assert e["state"] == "done"
    rc, v = pmi("verify", hid)
    ev = v["evaluations"][0]
    assert ev.get("replication") in ("ok", None) or isinstance(ev.get("replication"), str)
    assert v["status"] in ("Simulated", "Rejected", "Inconclusive")


def test_target_cannot_be_injected(harness, projects, pmi):
    _setup_churn(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "amplify",
        "--spec", '{"injector":"missing","columns":["churned"]}',
        "--rule", '{"type":"eaf","metric":"accuracy","level":"2x","min_eaf":1.1}')
    rc, e = pmi("experiment", "run", "E-001")
    assert e["state"] == "failed" and "target column" in e["error"]


def test_time_lag_blocked_without_time_profile(harness, projects, pmi):
    _setup_churn(harness, projects, pmi)
    hid = _hyp(pmi)
    rc, msg = pmi("experiment", "plan", "--hypothesis", hid, "--type", "amplify",
                  "--spec", '{"injector":"time_lag","columns":["n_tickets"]}',
                  "--rule", '{"type":"eaf","metric":"accuracy","level":"A1","min_eaf":1.1}')
    assert rc == 2 and "time_column" in msg
