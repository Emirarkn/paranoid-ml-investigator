"""Install the agent configuration (claude_config/ -> .claude/). Run once, by a human:

    python setup_claude_config.py            # copies new files, never overwrites changed ones
    python setup_claude_config.py --force    # overwrite .claude/ files with claude_config/ versions

claude_config/ is the version-controlled source of the agent's subagents, skills, hooks and
permission settings. Claude Code reads them from .claude/.
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC, DST = ROOT / "claude_config", ROOT / ".claude"


def main() -> int:
    force = "--force" in sys.argv
    copied, same, conflicts = [], [], []
    for p in sorted(SRC.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(SRC)
        out = DST / rel
        if out.exists():
            if filecmp.cmp(p, out, shallow=False):
                same.append(rel)
                continue
            if not force:
                conflicts.append(rel)
                continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        copied.append(rel)
    print(f"copied: {len(copied)}  unchanged: {len(same)}  conflicts (skipped): {len(conflicts)}")
    for c in conflicts:
        print(f"  differs, not overwritten: .claude/{c.as_posix()}  (use --force)")
    if copied or same:
        print("Done. Start Claude Code in this folder (with the venv active): claude")
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
