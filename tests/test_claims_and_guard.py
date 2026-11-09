"""Agent-hallucination controls: claim checker + guard hook."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.test_evidence import _hyp, _setup_retail

REPO = Path(__file__).resolve().parents[1]
GUARD = next(p for p in (REPO / ".claude" / "hooks" / "guard.py", REPO / "claude_config" / "hooks" / "guard.py")
             if p.is_file())


def test_claim_checker(harness, projects, pmi):
    run_dir = _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"target_proxy","data_via":"profile"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-001")
    notes = run_dir / "notes" / "n.md"
    notes.write_text("H-001 is verified.\nThe model improved.\ntrain.py:999 is wrong.\nCorrelation 0.73 (E-001).\n"
                     "H-009 matters.\n", encoding="utf-8")
    rc, out = pmi("check-claims", str(notes))
    issues = " | ".join(i["issue"] for i in out["issues"])
    assert rc == 1
    assert "H-001 is described as verified but its status is Suspected" in issues
    assert "improvement claim" in issues
    assert "line 999 does not exist" in issues
    assert "number 0.73 not found" in issues
    assert "unknown id H-009" in issues
    pmi("verify", hid)
    notes.write_text("H-001 is verified (E-001); correlation with the future target is 1.0, see train.py:10.\n",
                     encoding="utf-8")
    rc, out = pmi("check-claims", str(notes))
    assert rc == 0, out


def _guard(payload: dict, project: Path, env_extra=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project), **(env_extra or {}))
    return subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload), text=True,
                          capture_output=True, env=env)


def test_guard_hook(harness, projects, pmi):
    run_dir = _setup_retail(harness, projects, pmi)
    target = projects / "retail_weekly"
    # harness is the "project dir" for the hook
    (harness / ".claude").mkdir(exist_ok=True)
    cases = [
        ({"tool_name": "Write", "tool_input": {"file_path": str(target / "train.py")}}, 2),
        ({"tool_name": "Edit", "tool_input": {"file_path": str(run_dir / "workspace" / "target" / "train.py")}}, 2),
        ({"tool_name": "Write", "tool_input": {"file_path": str(run_dir / "ledger.sqlite")}}, 2),
        ({"tool_name": "Write", "tool_input": {"file_path": str(run_dir / "artifacts" / "E-001" / "x.json")}}, 2),
        ({"tool_name": "Write", "tool_input": {"file_path": str(harness / "config" / "policy.yaml")}}, 2),
        ({"tool_name": "Write", "tool_input": {"file_path": str(run_dir / "workspace" / "pmi_adapter.py")}}, 0),
        ({"tool_name": "Write", "tool_input": {"file_path": str(run_dir / "notes" / "a.md")}}, 0),
        ({"tool_name": "Bash", "tool_input": {"command": f"echo x > {target}/train.py"}}, 2),
        ({"tool_name": "Bash", "tool_input": {"command": f"sqlite3 {run_dir}/ledger.sqlite 'update ...'"}}, 2),
        ({"tool_name": "Bash", "tool_input": {"command": "pmi status"}}, 0),
        ({"tool_name": "Bash", "tool_input": {"command": f"cat {target}/train.py"}}, 0),
    ]
    for payload, expected in cases:
        r = _guard(payload, harness)
        assert r.returncode == expected, (payload, r.stderr)
    dev = _guard({"tool_name": "Write", "tool_input": {"file_path": str(harness / "config" / "policy.yaml")}},
                 harness, {"PMI_DEV_MODE": "1"})
    assert dev.returncode == 0
    still = _guard({"tool_name": "Write", "tool_input": {"file_path": str(target / "train.py")}},
                   harness, {"PMI_DEV_MODE": "1"})
    assert still.returncode == 2
