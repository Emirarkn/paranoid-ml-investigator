"""Claim checker — catches the agent's own hallucinations in narrative notes.

Checks (heuristic, conservative):
  * file:line references exist in the workspace copy and the line number is in range
  * H-xxx / E-xxx ids exist
  * a sentence that says "verified"/"proven" about H-xxx requires that H to be Verified
  * a verification word with no H-id at all is an unanchored claim
  * numbers in a sentence that cites E-xxx must appear in that experiment's recorded result
  * "improved / fixed" claims must cite an experiment

Wording lists are multilingual (English + Turkish) because the agent writes notes in the user's language.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pmi.core.run import Run
from pmi.evidence.ledger import Ledger

VERIFY_WORDS = re.compile(r"\b(verified|doğrulan\w*|dogrulan\w*|kanıtlan\w*|kanitlan\w*|proven|kesinleş\w*)\b", re.I)
IMPROVE_WORDS = re.compile(r"\b(improv\w*|iyileş\w*|düzel\w*|fixed)\b", re.I)
FILE_REF = re.compile(r"([\w./\\-]+\.(?:py|ipynb|sql|r|yaml|yml|toml|csv)):(\d+)")
ID_REF = re.compile(r"\b([HE]-\d{3})\b")
NUM = re.compile(r"(%?)(?<![\w.-])([-+]?\d+(?:[.,]\d+)?)(\s*%?)")


def _numbers(obj: Any, out: list[float]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(float(obj))
    elif isinstance(obj, str):
        for m in re.findall(r"[-+]?\d+(?:\.\d+)?", obj):
            out.append(float(m))


def _sentences(text: str) -> list[tuple[int, str]]:
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        for s in re.split(r"(?<=[.!?])\s+", line):
            if s.strip():
                out.append((ln, s.strip()))
    return out


def _matches(x: float, pool: list[float], percent: bool, decimals: int) -> bool:
    """x as written must be a rounding of a recorded value (percent: x/100 also allowed)."""
    cands = [(x, decimals)]
    if percent:   # 12% may mean 0.12, or a 12% change = factor 1.12 / 0.88
        cands += [(x / 100.0, decimals + 2), (1 + x / 100.0, decimals + 2), (1 - x / 100.0, decimals + 2)]
    for c, dec in cands:
        half_ulp = 0.5 * 10 ** (-dec) + 1e-12
        for p in pool:
            if abs(c - p) <= half_ulp or (p != 0 and abs(c - p) / abs(p) <= 0.005):
                return True
    return False


def check_claims(run: Run, ledger: Ledger, path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    issues: list[dict[str, Any]] = []
    hyps = {h["id"]: h for h in ledger.list_hypotheses()}
    exps = {e["id"]: e for e in ledger.list_experiments()}
    for ln, sent in _sentences(text):
        for f, line in FILE_REF.findall(sent):
            p = run.target_copy / f.replace("\\", "/")
            if not p.is_file():
                p = run.root / f
            if not p.is_file():
                issues.append({"line": ln, "issue": f"referenced file does not exist: {f}", "text": sent[:200]})
                continue
            n = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
            if int(line) < 1 or int(line) > n:
                issues.append({"line": ln, "issue": f"{f} has {n} lines; line {line} does not exist", "text": sent[:200]})
        ids = ID_REF.findall(sent)
        for i in ids:
            if i not in hyps and i not in exps:
                issues.append({"line": ln, "issue": f"unknown id {i}", "text": sent[:200]})
        hids = sorted({i for i in ids if i.startswith("H-") and i in hyps})
        eids = sorted({i for i in ids if i.startswith("E-") and i in exps})
        if VERIFY_WORDS.search(sent) and not re.search(r"\b(not|değil|degil|henüz|unverified|doğrulanmadı|doğrulanamadı)\b", sent, re.I):
            if not hids and not eids:
                issues.append({"line": ln, "issue": "verification claim without an H-/E- id", "text": sent[:200]})
            for h in hids:
                if hyps[h]["status"] != "Verified":
                    issues.append({"line": ln, "issue": f"{h} is described as verified but its status is "
                                   f"{hyps[h]['status']}", "text": sent[:200]})
        if IMPROVE_WORDS.search(sent) and not eids:
            issues.append({"line": ln, "issue": "improvement claim without an experiment id (E-xxx)", "text": sent[:200]})
        if eids:
            pool: list[float] = []
            for e in eids:
                _numbers(exps[e]["result"], pool)
                _numbers(exps[e]["spec"], pool)
                _numbers(exps[e]["decision_rule"], pool)
            stripped = ID_REF.sub(" ", FILE_REF.sub(" ", sent))
            for pre, raw, post in NUM.findall(stripped):
                txt = raw.replace(",", ".")
                x = float(txt)
                dec = len(txt.split(".")[1]) if "." in txt else 0
                if dec == 0 and abs(x) <= 10:   # small integers (levels, counts) are too ambiguous
                    continue
                if not _matches(x, pool, "%" in pre + post, dec):
                    issues.append({"line": ln, "issue": f"number {raw} not found in recorded results of {', '.join(eids)}",
                                   "text": sent[:200]})
    return issues


def dump(issues: list[dict[str, Any]]) -> str:
    return json.dumps(issues, indent=2, ensure_ascii=False)
