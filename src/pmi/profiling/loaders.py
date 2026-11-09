"""Tabular loaders used by scans and data-level checks (never by the adapter)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TABULAR = {".csv", ".tsv", ".txt", ".parquet", ".xlsx", ".xls", ".feather", ".jsonl"}


def load_table(path: Path, nrows: int | None = None) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf in (".csv", ".tsv", ".txt"):
        sep = "\t" if suf == ".tsv" else None
        try:
            return pd.read_csv(path, sep=sep, engine="python", nrows=nrows)
        except Exception:
            return pd.read_csv(path, nrows=nrows, encoding="latin-1", sep=sep, engine="python")
    if suf == ".parquet":
        df = pd.read_parquet(path)
    elif suf in (".xlsx", ".xls"):
        df = pd.read_excel(path, nrows=nrows)
    elif suf == ".feather":
        df = pd.read_feather(path)
    elif suf == ".jsonl":
        df = pd.read_json(path, lines=True, nrows=nrows)
    else:
        raise ValueError(f"Unsupported table format: {suf}")
    return df.head(nrows) if nrows else df
