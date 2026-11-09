"""Stage 1 acceptance: read the project safely, inventory it, never modify it."""
from __future__ import annotations

import json

from pmi.core.config import file_sha256


def _hashes(root):
    return {p.relative_to(root).as_posix(): file_sha256(p) for p in root.rglob("*") if p.is_file()}


def test_init_scan_does_not_touch_target(harness, projects, pmi):
    target = projects / "retail_weekly"
    before = _hashes(target)
    rc, out = pmi("init", "--target", str(target), "--name", "t")
    assert rc == 0 and out["files_hashed"] == len(before)
    rc, scan = pmi("scan")
    assert rc == 0
    assert scan["inventory"]["code"] == 1 and scan["inventory"]["data"] == 1
    assert _hashes(target) == before
    rc, integ = pmi("integrity")
    assert rc == 0 and integ["ok"]


def test_integrity_detects_modified_target(harness, projects, pmi, tmp_path):
    import shutil
    target = tmp_path / "proj"
    shutil.copytree(projects / "churn_tabular", target)
    pmi("init", "--target", str(target))
    (target / "model.py").write_text("# changed\n", encoding="utf-8")
    rc, integ = pmi("integrity")
    assert rc == 3 and not integ["ok"] and integ["target"]["changed"] == ["model.py"]


def test_secrets_are_not_copied(harness, pmi, tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n")
    (proj / ".env").write_text("TOKEN=abc\n")
    rc, out = pmi("init", "--target", str(proj))
    run_dir = harness / "runs" / out["run_id"]
    assert not (run_dir / "workspace" / "target" / ".env").exists()
    assert ".env" not in json.loads((run_dir / "snapshot.json").read_text())


def test_target_cannot_contain_harness(harness, pmi):
    rc, msg = pmi("init", "--target", str(harness.parent))
    assert rc == 2
