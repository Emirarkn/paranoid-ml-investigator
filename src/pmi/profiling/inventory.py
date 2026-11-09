"""Project inventory: what kinds of files exist. No domain assumptions."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

KINDS = {
    "code": {".py", ".ipynb", ".r", ".sql", ".scala", ".jl", ".sh", ".ps1"},
    "data": {".csv", ".tsv", ".parquet", ".xlsx", ".xls", ".feather", ".json", ".jsonl", ".txt"},
    "config": {".yaml", ".yml", ".toml", ".ini", ".cfg", ".env.example"},
    "model": {".pkl", ".pickle", ".joblib", ".pt", ".pth", ".onnx", ".h5", ".keras", ".cbm", ".bin"},
    "docs": {".md", ".rst", ".pdf", ".docx", ".html"},
    "report": {".png", ".jpg", ".svg", ".pptx"},
}


def classify(path: Path) -> str:
    suf = path.suffix.lower()
    name = path.name.lower()
    if suf == ".json" and any(k in name for k in ("config", "param", "setting")):
        return "config"
    for kind, exts in KINDS.items():
        if suf in exts:
            return kind
    return "other"


def build_inventory(copy_root: Path, snapshot: dict[str, dict[str, Any]]) -> dict[str, Any]:
    files = []
    for rel, meta in snapshot.items():
        p = copy_root / rel
        kind = classify(Path(rel))
        entry = {"path": rel, "kind": kind, "bytes": meta["bytes"], "in_workspace": p.is_file()}
        if kind == "code" and p.is_file() and p.suffix.lower() != ".ipynb":
            try:
                entry["lines"] = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
            except OSError:
                pass
        files.append(entry)
    counts = Counter(f["kind"] for f in files)
    return {"n_files": len(files), "by_kind": dict(counts), "files": files}
