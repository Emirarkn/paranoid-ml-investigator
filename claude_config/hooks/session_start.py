#!/usr/bin/env python3
"""SessionStart: give the agent the current investigation state so it resumes instead of rescanning."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
env = dict(os.environ, PMI_HOME=str(proj))
lines = ["[PMI] Paranoid ML Investigator session."]
if os.environ.get("PMI_DEV_MODE") == "1":
    lines.append("[PMI] PMI_DEV_MODE=1 -> harness files are editable (originals and evidence stay protected).")
try:
    r = subprocess.run([sys.executable, "-m", "pmi", "status"], capture_output=True, text=True, env=env, timeout=60)
    if r.returncode == 0:
        st = json.loads(r.stdout)
        unconfirmed = [k for k, v in st["profile"].items() if v != "confirmed"]
        lines += [f"[PMI] Active run: {st['run']} -> target {st['target']}",
                  f"[PMI] Adapter: {st['adapter']}",
                  f"[PMI] Unconfirmed profile fields: {', '.join(unconfirmed) or 'none'}",
                  f"[PMI] Hypotheses: " + ", ".join(f"{h['id']}={h['status']}" for h in st["hypotheses"]),
                  f"[PMI] Budget: {st['budget']}"]
    else:
        lines.append("[PMI] " + (r.stderr.strip() or "no active run") +
                     " — ask the human which project to investigate, then `pmi init --target <folder>`.")
except FileNotFoundError:
    lines.append("[PMI] pmi is not installed in this Python. Ask the human to run: pip install -e .")
except Exception as exc:  # never block the session
    lines.append(f"[PMI] status unavailable: {exc}")
print("\n".join(lines))
