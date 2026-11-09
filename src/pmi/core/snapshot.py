"""Read-only handling of the investigated project: hashing, isolated copy, integrity check."""
from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path
from typing import Any

from pmi.core.config import file_sha256


def _excluded(rel: Path, exclude_dirs: list[str], exclude_globs: list[str]) -> bool:
    if any(part in exclude_dirs for part in rel.parts[:-1]):
        return True
    name = rel.name
    return any(fnmatch.fnmatch(name.lower(), g.lower()) for g in exclude_globs)


def iter_files(root: Path, policy: dict[str, Any]):
    t = policy.get("target", {})
    ex_dirs = list(t.get("exclude_dirs", []))
    ex_globs = list(t.get("exclude_globs", []))
    for p in sorted(root.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        rel = p.relative_to(root)
        if _excluded(rel, ex_dirs, ex_globs):
            continue
        yield p, rel


def take_snapshot(root: Path, policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """sha256 + size for every non-excluded file. Never writes to root."""
    snap: dict[str, dict[str, Any]] = {}
    for p, rel in iter_files(root, policy):
        st = p.stat()
        snap[rel.as_posix()] = {"sha256": file_sha256(p), "bytes": st.st_size}
    return snap


def copy_to_workspace(root: Path, dest: Path, snapshot: dict[str, dict[str, Any]],
                      policy: dict[str, Any]) -> dict[str, Any]:
    t = policy.get("target", {})
    max_file = float(t.get("max_file_mb_for_copy", 200)) * 1024 * 1024
    max_total = float(t.get("max_total_mb_for_copy", 2000)) * 1024 * 1024
    copied, skipped, total = [], [], 0
    for rel, meta in snapshot.items():
        size = meta["bytes"]
        if size > max_file or total + size > max_total:
            skipped.append({"file": rel, "bytes": size, "reason": "size limit (policy.target)"})
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, out)
        total += size
        copied.append(rel)
    return {"copied": len(copied), "skipped": skipped, "bytes_copied": total}


def diff_snapshot(old: dict[str, dict[str, Any]], new: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k]["sha256"] != new[k]["sha256"])
    return {"added": added, "removed": removed, "changed": changed}
