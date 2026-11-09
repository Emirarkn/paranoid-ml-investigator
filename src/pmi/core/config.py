"""Locating the harness root and loading policy files."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import yaml


class PMIError(RuntimeError):
    """Expected, user-facing error (printed without a traceback)."""


def harness_root(start: Path | None = None) -> Path:
    """Directory that holds config/policy.yaml. PMI_HOME overrides discovery."""
    env = os.environ.get("PMI_HOME")
    if env:
        return Path(env).resolve()
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "config" / "policy.yaml").is_file():
            return p
    raise PMIError(
        "Harness root not found (no config/policy.yaml above the current directory). "
        "Run pmi from inside the paranoid-ml-investigator folder or set PMI_HOME."
    )


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_policy(root: Path) -> dict[str, Any]:
    return load_yaml(root / "config" / "policy.yaml")


def load_amplification(root: Path) -> dict[str, Any]:
    return load_yaml(root / "config" / "amplification.yaml")


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
