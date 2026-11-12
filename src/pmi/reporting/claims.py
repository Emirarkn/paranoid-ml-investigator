"""Claim checker — catches the agent's own hallucinations in narrative notes.

Checks (heuristic, conservative):
  * file:line references exist in the workspace copy and the line number is in range
  * H-xxx / E-xxx ids exist
  * a sentence that says "verified"/"proven" about H-xxx requires that H to be Verified
  * a verification word with no H-id at all is an unanchored claim
  * numbers in a sentence that cites E-xxx must appear in that experiment's recorded result
  * "improved / fixed" claims must cite an experiment

Wording lists are multilingual (English + Turkish) because the agent writes notes in the user's language.

Prophecy mode (files named prophecies*.md / prophecy*.md, or `--mode prophecy`):
  The prophet subagent may exaggerate consequences, but may not change facts. So in this mode
  * dramatic wording and "fixed/improved" words are allowed
  * any verification word ("verified", "doğrulandı", "kanıtlandı") is an issue: only `pmi verify` decides status
  * a status tag "H-xxx [Status]" must match the ledger
  * a number cited with E-xxx must still match the recorded result
  * a number without an E-id is allowed only inside a prophecy block that has a "Varsayım:" line
  * every "## Kehanet" block needs "Dayanak:" (a known H-id or DAYANAKSIZ) and "Çürütme:" lines
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
NEGATION = re.compile(r"\b(not|değil|degil|henüz|unverified|doğrulanmadı|doğrulanamadı)\b", re.I)

PROPHECY_FILE = re.compile(r"^prophec(y|ies)", re.I)
PROPHECY_HEAD = re.compile(r"^#{2,3}\s+(kehanet|prophecy)\b", re.I)
STATUS_TAG = re.compile(r"\b(H-\d{3})\s*\[(Verified|Simulated|Suspected|Inconclusive|Rejected)\]", re.I)
UNSUPPORTED = re.compile(r"dayanaks[ıi]z|unsupported", re.I)


def _field(name: str) -> re.Pattern:
    return re.compile(rf"^[\s>*_-]*({name})\**\s*:", re.I)


BASIS, FALSIFIER, ASSUMPTION = _field("dayanak|basis"), _field("çürütme|curutme|falsifier"), _field("varsayım|varsayim|assumption")


def is_prophecy_file(path: Path) -> bool:
    return bool(PROPHECY_FILE.match(Path(path).name))


def _prophecy_blocks(text: str) -> list[dict[str, Any]]:
    """Split a prophecy file into '## Kehanet' blocks: start/end line (1-based, inclusive) and the block lines."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines, 1) if PROPHECY_HEAD.match(line)]
    blocks = []
    for k, s in enumerate(starts):
        e = (starts[k + 1] - 1) if k + 1 < len(starts) else len(lines)
        body = lines[s - 1:e]
        blocks.append({"start": s, "end": e, "title": body[0].strip(), "lines": body,
                       "assumption": any(ASSUMPTION.match(x) for x in body)})
    return blocks


def _speculative_number(raw: str) -> bool:
    """Numbers worth policing: not small counts/levels (≤ 10) and not calendar years."""
    x = float(raw.replace(",", "."))
    if "." not in raw and "," not in raw and (abs(x) <= 10 or 1900 <= x <= 2100):
        return False
    return True


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


def check_claims(run: Run, ledger: Ledger, path: Path, mode: str = "auto") -> list[dict[str, Any]]:
    """mode: auto (prophecy if the file is named prophecies*.md), findings, or prophecy."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    prophecy = mode == "prophecy" or (mode == "auto" and is_prophecy_file(path))
    issues: list[dict[str, Any]] = []
    hyps = {h["id"]: h for h in ledger.list_hypotheses()}
    exps = {e["id"]: e for e in ledger.list_experiments()}
    blocks = _prophecy_blocks(text) if prophecy else []
    if prophecy:
        issues += _prophecy_structure(blocks, hyps)
    for ln, sent in _sentences(text):
        if prophecy:
            issues += _prophecy_sentence(ln, sent, hyps, exps, blocks)
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
        if prophecy:
            continue
        hids = sorted({i for i in ids if i.startswith("H-") and i in hyps})
        eids = sorted({i for i in ids if i.startswith("E-") and i in exps})
        if VERIFY_WORDS.search(sent) and not NEGATION.search(sent):
            if not hids and not eids:
                issues.append({"line": ln, "issue": "verification claim without an H-/E- id", "text": sent[:200]})
            for h in hids:
                if hyps[h]["status"] != "Verified":
                    issues.append({"line": ln, "issue": f"{h} is described as verified but its status is "
                                   f"{hyps[h]['status']}", "text": sent[:200]})
        if IMPROVE_WORDS.search(sent) and not eids:
            issues.append({"line": ln, "issue": "improvement claim without an experiment id (E-xxx)", "text": sent[:200]})
        if eids:
            issues += _number_issues(ln, sent, eids, exps)
    return issues


def _number_issues(ln: int, sent: str, eids: list[str], exps: dict[str, Any]) -> list[dict[str, Any]]:
    """Numbers in a sentence that cites E-ids must be roundings of that experiment's recorded values."""
    issues = []
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


def _prophecy_structure(blocks: list[dict[str, Any]], hyps: dict[str, Any]) -> list[dict[str, Any]]:
    if not blocks:
        return [{"line": 1, "issue": "prophecy file has no '## Kehanet' block", "text": ""}]
    issues = []
    for b in blocks:
        basis = [x for x in b["lines"] if BASIS.match(x)]
        if not basis:
            issues.append({"line": b["start"], "issue": "prophecy without a 'Dayanak:' line (H-id or DAYANAKSIZ)",
                           "text": b["title"][:200]})
        elif not any(UNSUPPORTED.search(x) or any(i in hyps for i in ID_REF.findall(x)) for x in basis):
            issues.append({"line": b["start"], "issue": "'Dayanak:' must cite a known H-id or say DAYANAKSIZ",
                           "text": basis[0][:200]})
        if not any(FALSIFIER.match(x) for x in b["lines"]):
            issues.append({"line": b["start"], "issue": "prophecy without a 'Çürütme:' line (what would prove it wrong)",
                           "text": b["title"][:200]})
    return issues


def _prophecy_sentence(ln: int, sent: str, hyps: dict[str, Any], exps: dict[str, Any],
                       blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for h, status in STATUS_TAG.findall(sent):
        if h in hyps and status.lower() != hyps[h]["status"].lower():
            issues.append({"line": ln, "issue": f"{h} is tagged [{status}] but its status is {hyps[h]['status']}",
                           "text": sent[:200]})
    if VERIFY_WORDS.search(sent) and not NEGATION.search(sent):
        issues.append({"line": ln, "issue": "a prophecy cannot claim verification; only `pmi verify` decides status",
                       "text": sent[:200]})
    eids = sorted({i for i in ID_REF.findall(sent) if i.startswith("E-") and i in exps})
    if eids:
        return issues + _number_issues(ln, sent, eids, exps)
    block = next((b for b in blocks if b["start"] <= ln <= b["end"]), None)
    if block is None or not block["assumption"]:
        stripped = ID_REF.sub(" ", FILE_REF.sub(" ", sent))
        for _, raw, _ in NUM.findall(stripped):
            if _speculative_number(raw):
                issues.append({"line": ln, "issue": f"speculative number {raw} without an E-id needs a 'Varsayım:' "
                               "line in its prophecy block", "text": sent[:200]})
    return issues


def dump(issues: list[dict[str, Any]]) -> str:
    return json.dumps(issues, indent=2, ensure_ascii=False)
