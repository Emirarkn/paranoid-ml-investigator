"""Parent side of experiment execution: builds the job, runs the worker subprocess."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pmi
from pmi.core.config import load_amplification
from pmi.core.run import Run


def confirmed_values(profile: dict[str, Any]) -> dict[str, Any]:
    return {k: v["value"] for k, v in profile["fields"].items() if v.get("status") == "confirmed"}


def run_job(run: Run, jtype: str, spec: dict[str, Any], artifacts_dir: Path, seeds: list[int],
            adapter: dict[str, Any] | None, profile: dict[str, Any]) -> dict[str, Any]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    policy = run.policy
    job = {"type": jtype, "workspace": str(run.workspace), "adapter": adapter, "spec": spec,
           "profile": confirmed_values(profile), "amp": load_amplification(run.root), "seeds": seeds,
           "artifacts_dir": str(artifacts_dir),
           "network": policy.get("execution", {}).get("network", "blocked")}
    job_path, out_path = artifacts_dir / "job.json", artifacts_dir / "worker_out.json"
    job_path.write_text(json.dumps(job, indent=2, default=str), encoding="utf-8")
    if out_path.exists():
        out_path.unlink()
    env = os.environ.copy()
    src = str(Path(pmi.__file__).resolve().parent.parent)
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.pop("HTTP_PROXY", None), env.pop("HTTPS_PROXY", None)
    timeout = int(policy.get("execution", {}).get("timeout_seconds_per_experiment", 900))
    try:
        proc = subprocess.run([sys.executable, "-m", "pmi.engine.worker", str(job_path), str(out_path)],
                              cwd=str(run.workspace), env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after {timeout}s (policy.execution.timeout_seconds_per_experiment)"}
    if not out_path.is_file():
        return {"ok": False, "error": f"Worker crashed (exit {proc.returncode}): {proc.stderr[-2000:]}"}
    out = json.loads(out_path.read_text(encoding="utf-8"))
    if proc.stdout.strip():
        (artifacts_dir / "stdout.txt").write_text(proc.stdout[-20000:], encoding="utf-8")
    return out
