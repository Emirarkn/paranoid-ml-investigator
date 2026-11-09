"""Static code scan (AST). Produces facts with real file:line references.

Two outputs:
  * facts    — what the code does (imports, models, splits, metrics, data reads, target hints)
  * patterns — static leakage / evaluation smells. These are SUSPICIONS, never findings:
               they must be turned into hypotheses and tested (`pmi checks` / experiments).
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

TRANSFORMER_HINT = re.compile(r"(Scaler|Encoder|Imputer|PCA|Vectorizer|Normalizer|Discretizer|"
                              r"Select|Transformer|Binarizer|SVD|Embedding)", re.I)
MODEL_HINT = re.compile(r"(Regressor|Classifier|Regression|ARIMA|SARIMAX|Prophet|ExponentialSmoothing|"
                        r"Holt|LGBM|XGB|CatBoost|Forest|Boost|SVC|SVR|KNeighbors|MLP|Network|Model)$")
METRICS = {"mean_absolute_error", "mean_squared_error", "root_mean_squared_error", "r2_score",
           "accuracy_score", "f1_score", "roc_auc_score", "mean_absolute_percentage_error",
           "log_loss", "precision_score", "recall_score", "balanced_accuracy_score",
           "median_absolute_error", "mean_pinball_loss"}
SPLITTERS = {"train_test_split", "TimeSeriesSplit", "KFold", "StratifiedKFold", "GroupKFold",
             "ShuffleSplit", "GroupShuffleSplit", "cross_val_score", "cross_validate",
             "GridSearchCV", "RandomizedSearchCV", "PredefinedSplit"}
READERS = {"read_csv", "read_excel", "read_parquet", "read_feather", "read_json", "read_sql",
           "read_table", "load"}
TIME_HINTS = ("to_datetime", "resample", "Grouper", "TimeSeriesSplit", "rolling", "date_range")


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""


def _src(node: ast.AST, text: str) -> str:
    seg = ast.get_source_segment(text, node) or ""
    return " ".join(seg.split())[:160]


def _const_str(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _notebook_source(path: Path) -> tuple[str, list[str]]:
    """Concatenate code cells; return text and a per-line location label."""
    nb = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    lines, labels = [], []
    for ci, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        for li, line in enumerate(src.splitlines(), 1):
            if line.lstrip().startswith(("%", "!")):
                line = "# " + line   # magics are not python
            lines.append(line)
            labels.append(f"cell{ci}:{li}")
        lines.append("")
        labels.append(f"cell{ci}:end")
    return "\n".join(lines), labels


def scan_file(path: Path, rel: str, temporal_names: set[str]) -> dict[str, Any]:
    labels: list[str] | None = None
    if path.suffix.lower() == ".ipynb":
        text, labels = _notebook_source(path)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {"file": rel, "parse_error": str(exc)}

    def loc(node: ast.AST) -> str:
        ln = getattr(node, "lineno", 0)
        if labels and 0 < ln <= len(labels):
            return f"{rel}#{labels[ln - 1]}"
        return f"{rel}:{ln}"

    facts: dict[str, list] = {k: [] for k in ("imports", "models", "splits", "metrics", "reads",
                                               "target_hints", "fits", "shifts", "drops", "feature_lists")}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            facts["imports"] += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            facts["imports"].append(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            fn = _name(node.func)
            if fn in SPLITTERS:
                kw = {k.arg: _src(k.value, text) for k in node.keywords if k.arg}
                facts["splits"].append({"call": fn, "kwargs": kw, "at": loc(node), "line": node.lineno,
                                        "code": _src(node, text)})
            elif fn in METRICS:
                facts["metrics"].append({"metric": fn, "at": loc(node)})
            elif fn in READERS and node.args:
                facts["reads"].append({"call": fn, "arg": _const_str(node.args[0]) or _src(node.args[0], text),
                                       "at": loc(node)})
            elif fn and MODEL_HINT.search(fn) and isinstance(node.func, (ast.Name, ast.Attribute)) \
                    and fn[0].isupper():
                facts["models"].append({"class": fn, "at": loc(node)})
            elif fn in ("fit", "fit_transform", "fit_predict"):
                obj = _src(node.func.value, text) if isinstance(node.func, ast.Attribute) else ""
                arg = _src(node.args[0], text) if node.args else ""
                facts["fits"].append({"method": fn, "object": obj, "arg": arg, "at": loc(node),
                                      "line": node.lineno})
            elif fn == "shift":
                val = None
                if node.args:
                    val = node.args[0]
                for k in node.keywords:
                    if k.arg == "periods":
                        val = k.value
                if isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.USub):
                    facts["shifts"].append({"periods": "-" + _src(val.operand, text), "at": loc(node),
                                            "code": _src(node, text)})
            elif fn == "drop":
                for k in node.keywords:
                    if k.arg == "columns":
                        facts["drops"].append({"columns": _src(k.value, text), "at": loc(node)})
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            tname = _name(node.targets[0]) if isinstance(node.targets[0], (ast.Name, ast.Attribute)) else ""
            low = tname.lower()
            if isinstance(node.value, (ast.List, ast.Tuple)) and node.value.elts and \
                    all(_const_str(e) is not None for e in node.value.elts) and \
                    any(k in low for k in ("feat", "col", "predictor", "input", "regressor", "x_")):
                facts["feature_lists"].append({"name": tname, "columns": [_const_str(e) for e in node.value.elts],
                                               "at": loc(node)})
            if low in ("y", "y_train", "target", "target_col", "target_column", "label", "label_col", "ycol", "y_col"):
                v = node.value
                col = _const_str(v)
                if col is None and isinstance(v, ast.Subscript):
                    col = _const_str(v.slice)
                if col is None and isinstance(v, ast.Attribute) and low.startswith("y"):
                    col = v.attr
                if col:
                    facts["target_hints"].append({"column": col, "at": loc(node), "code": _src(node, text)})

    facts["imports"] = sorted(set(facts["imports"]))
    patterns = _patterns(facts, text, rel, temporal_names)
    for k in ("splits", "fits"):
        for d in facts[k]:
            d.pop("line", None)
    return {"file": rel, "facts": facts, "patterns": patterns}


def _patterns(facts: dict[str, list], text: str, rel: str, temporal_names: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    split_lines = [s["line"] for s in facts["splits"] if s["call"] == "train_test_split"]
    first_split = min(split_lines) if split_lines else None
    temporal_file = any(h in text for h in TIME_HINTS) or any(
        re.search(r"['\"]" + re.escape(n) + r"['\"]", text) for n in temporal_names)

    for f in facts["fits"]:
        arg = f["arg"].lower()
        if "test" in arg or "valid" in arg or "holdout" in arg:
            out.append({"pattern": "fit_on_evaluation_data", "at": f["at"], "confidence": "medium",
                        "code": f"{f['object']}.{f['method']}({f['arg']})",
                        "note": "A fit-type call receives data named like test/validation."})
        is_transformer = bool(TRANSFORMER_HINT.search(f["object"])) or f["method"] == "fit_transform"
        if first_split and f["line"] < first_split and is_transformer and "train" not in arg:
            out.append({"pattern": "preprocessing_fit_before_split", "at": f["at"], "confidence": "medium",
                        "code": f"{f['object']}.{f['method']}({f['arg']})",
                        "note": "A transformer is fitted before train_test_split is called in this file; "
                                "statistics of evaluation rows may leak into training."})
    for s in facts["splits"]:
        shuffle = s["kwargs"].get("shuffle")
        if s["call"] == "train_test_split" and temporal_file and shuffle not in ("False", "0"):
            out.append({"pattern": "random_split_with_temporal_data", "at": s["at"], "confidence": "low",
                        "code": s["code"],
                        "note": "Random (shuffled) split in a file that handles temporal data. Only a problem "
                                "if rows are time-ordered observations that must be predicted forward in time."})
        if s["call"] in ("KFold", "StratifiedKFold") and temporal_file and shuffle in ("True", "1"):
            out.append({"pattern": "shuffled_kfold_with_temporal_data", "at": s["at"], "confidence": "low",
                        "code": s["code"], "note": "Shuffled K-fold where data looks temporal."})
    for sh in facts["shifts"]:
        out.append({"pattern": "negative_shift_future_values", "at": sh["at"], "confidence": "low",
                    "code": sh["code"],
                    "note": "shift(-k) pulls FUTURE values onto the current row. Legitimate when building the "
                            "target; leakage when the result is used as a feature."})
    return out


def scan_code(copy_root: Path, inventory: dict[str, Any], temporal_names: set[str]) -> dict[str, Any]:
    files = []
    for f in inventory["files"]:
        p = copy_root / f["path"]
        if f["kind"] != "code" or not p.is_file() or p.suffix.lower() not in (".py", ".ipynb"):
            continue
        files.append(scan_file(p, f["path"], temporal_names))
    patterns = [dict(p, file=r["file"]) for r in files for p in r.get("patterns", [])]
    return {"files": files, "patterns": patterns}
