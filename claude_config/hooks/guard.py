#!/usr/bin/env python3
"""PreToolUse guard for the Paranoid ML Investigator.

Blocks (exit code 2, reason on stderr -> shown to the agent):
  * any write to an investigated ORIGINAL project (read from runs/*/manifest.json)
  * any write to the workspace copy  runs/<id>/workspace/target/**   (the baseline must stay identical)
  * direct writes to evidence: ledger.sqlite, manifest/snapshot/profile/adapter/budget json,
    artifacts/**, scan/**  — these are written by `pmi` only
  * writes to harness files (src/, config/, .claude/, claude_config/, tests/, CLAUDE.md) unless PMI_DEV_MODE=1
  * reading benchmark answer keys (_answer_key.json)
  * Bash and PowerShell commands that combine a protected path (in any spelling: C:\\x, C:/x, /c/x)
    with a write-like operation

This is a guard, not a sandbox: an indirect Bash write can slip through. The hash-based
`pmi integrity` check (target, workspace copy, ledger chain) is the backstop.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PMI_ONLY = {"ledger.sqlite", "manifest.json", "snapshot.json", "profile.json", "adapter.json",
            "budget.json", "report.md"}
EVIDENCE_DIRS = {"artifacts", "scan", "adapter_validation"}
HARNESS = ["src", "config", ".claude", "claude_config", "setup_claude_config.py", "tests", "CLAUDE.md", "domain_packs",
           "pyproject.toml"]
WRITE_LIKE = re.compile(
    r"(>>?|\btee\b|\brm\b|\bdel\b|\bmv\b|\bcp\b|\bsed\s+-i|\bperl\s+-[a-z]*i|\bset-content\b|\badd-content\b|"
    r"\bout-file\b|\bremove-item\b|\bmove-item\b|\bcopy-item\b|\brename-item\b|\btruncate\b|\bunlink\b|"
    r"\bchmod\b|\bsqlite3\b|\bgit\s+(commit|checkout|reset|clean|stash|restore|rm|mv|apply|am|pull|merge|rebase)\b|"
    r"\bnew-item\b|\bclear-content\b|\bwrite(all)?(text|bytes|lines)\b|\bappendall(text|lines)\b|"
    r"open\([^)]*['\"][wa]b?\+?['\"]|\.write_text\(|\.write_bytes\(|to_csv\(|to_parquet\(|to_excel\()",
    re.I)
SHELL_TOOLS = ("Bash", "PowerShell")
# A drive letter that starts a path anywhere in a text ("C:\x", "C:/x"); the lookbehind keeps URLs ("https://") intact.
DRIVE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]):/")


def norm(p: str) -> str:
    s = p.replace("\\", "/").rstrip("/")
    m = re.match(r"^([a-zA-Z]):/(.*)$", s)
    if m:  # C:/x  ->  /c/x  (Git Bash form) so both spellings compare equal
        s = f"/{m.group(1).lower()}/{m.group(2)}"
    return s.lower() if os.name == "nt" or m else s


def norm_command(cmd: str) -> str:
    """Normalise every path spelling inside a shell command, not only a leading one.

    `C:\\a\\b`, `C:/a/b` and `/c/a/b` all become `/c/a/b`, so a protected target matches however the
    command spells it. On Windows the result is lower-cased, like `norm`.
    """
    s = DRIVE.sub(lambda m: f"/{m.group(1).lower()}/", cmd.replace("\\", "/"))
    return s.lower() if os.name == "nt" else s


def block(reason: str) -> None:
    print(f"[pmi guard] BLOCKED: {reason}", file=sys.stderr)
    sys.exit(2)


def load_targets(proj: Path) -> list[str]:
    out = []
    for mf in (proj / "runs").glob("*/manifest.json"):
        try:
            out.append(norm(str(Path(json.loads(mf.read_text(encoding="utf-8"))["target_path"]).resolve())))
        except Exception:
            continue
    return out


def path_reason(raw: str, proj: Path, targets: list[str], dev: bool) -> str | None:
    p = Path(raw)
    if not p.is_absolute():
        p = proj / p
    p = p.resolve()
    np_ = norm(str(p))
    for t in targets:
        if np_ == t or np_.startswith(t + "/"):
            return f"{p} is inside an investigated project ({t}); originals are read-only."
    runs = norm(str((proj / "runs").resolve()))
    if np_.startswith(runs + "/"):
        parts = np_[len(runs) + 1:].split("/")
        if parts[0] == "current":
            return "runs/CURRENT is managed by pmi (use `pmi use <run>`)."
        if len(parts) >= 2:
            if parts[1] in PMI_ONLY and len(parts) == 2:
                return f"{parts[1]} is written only by pmi commands."
            if parts[1] in EVIDENCE_DIRS:
                return f"{parts[1]}/ holds evidence written only by pmi."
            if parts[1] == "workspace" and len(parts) >= 3 and parts[2] == "target":
                return "workspace/target is the frozen copy of the project; never edit it."
        return None
    if not dev:
        for h in HARNESS:
            hp = norm(str((proj / h).resolve()))
            if np_ == hp or np_.startswith(hp + "/"):
                return (f"{h} belongs to the harness and is protected during investigations "
                        "(a human sets PMI_DEV_MODE=1 to develop the harness).")
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()).resolve()
    dev = os.environ.get("PMI_DEV_MODE") == "1"
    targets = load_targets(proj)

    if tool == "Read":
        if Path(ti.get("file_path", "")).name == "_answer_key.json":
            block("benchmark answer keys are hidden from the investigator.")
        sys.exit(0)

    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        raw = ti.get("file_path") or ti.get("notebook_path") or ""
        if raw:
            r = path_reason(raw, proj, targets, dev)
            if r:
                block(r)
        sys.exit(0)

    if tool in SHELL_TOOLS:
        cmd = ti.get("command", "")
        c_low = norm_command(cmd).lower()
        if "_answer_key" in c_low:
            block("benchmark answer keys are hidden from the investigator.")
        if re.match(r"^\s*(python\s+-m\s+)?pmi\b", cmd) and not WRITE_LIKE.search(cmd.split("pmi", 1)[1].replace("->", "")):
            sys.exit(0)
        writes = bool(WRITE_LIKE.search(cmd))
        protected = list(targets) + ["ledger.sqlite", "/artifacts/", "workspace/target", "manifest.json",
                                     "snapshot.json", "profile.json", "adapter.json", "runs/current"]
        if not dev:
            protected += ["config/policy.yaml", "config/amplification.yaml", ".claude/", "claude_config/", "src/pmi"]
        if writes:
            for t in protected:
                if t.lower() in c_low:
                    block(f"command writes near a protected location ({t}). Use pmi commands; originals and "
                          "evidence are read-only.")
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
