"""Evidence ledger (SQLite) with a tamper-evident hash chain.

* Hypotheses are created as `Suspected`. There is NO API to set a status directly:
  only `pmi.evidence.verify` changes it, and it writes the reason + experiment ids.
* Experiments are pre-registered (spec + decision rule hashed at plan time) before they run.
* Every mutation appends an event whose hash covers the previous event (hash chain), so a
  manual edit of the database is detected by `pmi integrity`.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pmi.core.config import PMIError, text_sha256
from pmi.core.run import utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY, created_at TEXT, title TEXT, statement TEXT, mechanism TEXT,
  expected_effect TEXT, falsification_test TEXT, kind TEXT, priority INTEGER,
  refs TEXT, affected_data TEXT, proposed_fix TEXT, origin TEXT,
  status TEXT, status_reason TEXT, status_at TEXT
);
CREATE TABLE IF NOT EXISTS experiments (
  id TEXT PRIMARY KEY, hypothesis_id TEXT, type TEXT, spec TEXT, decision_rule TEXT,
  spec_sha256 TEXT, planned_at TEXT, started_at TEXT, finished_at TEXT, state TEXT,
  adapter_kind TEXT, adapter_sha256 TEXT, adapter_fidelity TEXT,
  result TEXT, result_sha256 TEXT, artifacts TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, entity TEXT, entity_id TEXT,
  action TEXT, payload TEXT, prev_hash TEXT, hash TEXT
);
"""

KINDS = ("defect", "sensitivity")


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- event chain -------------------------------------------------------
    def _event(self, c: sqlite3.Connection, entity: str, eid: str, action: str, payload: dict) -> None:
        row = c.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else "GENESIS"
        at = utcnow()
        body = canonical(payload)
        h = hashlib.sha256(f"{prev}|{at}|{entity}|{eid}|{action}|{body}".encode()).hexdigest()
        c.execute("INSERT INTO events(at, entity, entity_id, action, payload, prev_hash, hash) "
                  "VALUES (?,?,?,?,?,?,?)", (at, entity, eid, action, body, prev, h))

    def verify_chain(self) -> dict[str, Any]:
        problems: list[str] = []
        with self._conn() as c:
            prev = "GENESIS"
            last_status: dict[str, str] = {}
            last_result: dict[str, str] = {}
            for e in c.execute("SELECT * FROM events ORDER BY seq"):
                h = hashlib.sha256(f"{prev}|{e['at']}|{e['entity']}|{e['entity_id']}|{e['action']}|{e['payload']}".encode()).hexdigest()
                if e["prev_hash"] != prev or e["hash"] != h:
                    problems.append(f"event #{e['seq']} hash mismatch (ledger edited outside pmi?)")
                prev = e["hash"]
                p = json.loads(e["payload"])
                if e["entity"] == "hypothesis" and "status" in p:
                    last_status[e["entity_id"]] = p["status"]
                if e["entity"] == "experiment" and "result_sha256" in p:
                    last_result[e["entity_id"]] = p["result_sha256"]
            for h_ in c.execute("SELECT id, status FROM hypotheses"):
                if last_status.get(h_["id"]) != h_["status"]:
                    problems.append(f"{h_['id']}: status '{h_['status']}' has no matching status event")
            for x in c.execute("SELECT id, result, result_sha256 FROM experiments WHERE result IS NOT NULL"):
                if text_sha256(x["result"]) != x["result_sha256"] or last_result.get(x["id"]) != x["result_sha256"]:
                    problems.append(f"{x['id']}: stored result does not match its recorded hash")
        return {"ok": not problems, "problems": problems}

    # ---- hypotheses --------------------------------------------------------
    def _next_id(self, c: sqlite3.Connection, table: str, prefix: str) -> str:
        n = c.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        return f"{prefix}-{n + 1:03d}"

    def add_hypothesis(self, *, title: str, statement: str, mechanism: str, expected_effect: str,
                       falsification_test: str, kind: str, priority: int = 3, refs: list[str] | None = None,
                       affected_data: str = "", proposed_fix: str = "", origin: str = "agent") -> str:
        if kind not in KINDS:
            raise PMIError(f"kind must be one of {KINDS}")
        for name, val in (("statement", statement), ("mechanism", mechanism),
                          ("falsification_test", falsification_test)):
            if not val or len(val.strip()) < 10:
                raise PMIError(f"Hypothesis needs a substantive --{name.replace('_', '-')} (>=10 chars).")
        with self._conn() as c:
            hid = self._next_id(c, "hypotheses", "H")
            now = utcnow()
            c.execute("INSERT INTO hypotheses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (hid, now, title, statement, mechanism, expected_effect, falsification_test, kind,
                       int(priority), canonical(refs or []), affected_data, proposed_fix, origin,
                       "Suspected", "registered; no experiment yet", now))
            self._event(c, "hypothesis", hid, "created", {"status": "Suspected", "title": title, "kind": kind})
        return hid

    def get_hypothesis(self, hid: str) -> dict[str, Any]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM hypotheses WHERE id=?", (hid,)).fetchone()
        if not r:
            raise PMIError(f"Hypothesis not found: {hid}")
        d = dict(r)
        d["refs"] = json.loads(d["refs"] or "[]")
        return d

    def list_hypotheses(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = [dict(r) for r in c.execute("SELECT * FROM hypotheses ORDER BY id")]
        for d in rows:
            d["refs"] = json.loads(d["refs"] or "[]")
        return rows

    def _set_status(self, hid: str, status: str, reason: str, payload: dict) -> None:
        """Private: called only by pmi.evidence.verify."""
        with self._conn() as c:
            c.execute("UPDATE hypotheses SET status=?, status_reason=?, status_at=? WHERE id=?",
                      (status, reason, utcnow(), hid))
            self._event(c, "hypothesis", hid, "status", dict(payload, status=status, reason=reason))

    def update_fix(self, hid: str, proposed_fix: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE hypotheses SET proposed_fix=? WHERE id=?", (proposed_fix, hid))
            self._event(c, "hypothesis", hid, "fix_proposed", {"proposed_fix": proposed_fix})

    # ---- experiments -------------------------------------------------------
    def plan_experiment(self, hid: str, etype: str, spec: dict, decision_rule: dict) -> str:
        self.get_hypothesis(hid)
        spec_txt, rule_txt = canonical(spec), canonical(decision_rule)
        with self._conn() as c:
            eid = self._next_id(c, "experiments", "E")
            sha = text_sha256(spec_txt + "|" + rule_txt)
            c.execute("INSERT INTO experiments(id, hypothesis_id, type, spec, decision_rule, spec_sha256, "
                      "planned_at, state) VALUES (?,?,?,?,?,?,?,?)",
                      (eid, hid, etype, spec_txt, rule_txt, sha, utcnow(), "planned"))
            self._event(c, "experiment", eid, "planned", {"hypothesis": hid, "type": etype, "spec_sha256": sha})
        return eid

    def get_experiment(self, eid: str) -> dict[str, Any]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM experiments WHERE id=?", (eid,)).fetchone()
        if not r:
            raise PMIError(f"Experiment not found: {eid}")
        d = dict(r)
        for k in ("spec", "decision_rule", "result", "artifacts"):
            d[k] = json.loads(d[k]) if d.get(k) else None
        return d

    def list_experiments(self, hid: str | None = None) -> list[dict[str, Any]]:
        q, args = "SELECT id FROM experiments", ()
        if hid:
            q, args = q + " WHERE hypothesis_id=?", (hid,)
        with self._conn() as c:
            ids = [r["id"] for r in c.execute(q + " ORDER BY id", args)]
        return [self.get_experiment(i) for i in ids]

    def count_experiments(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) AS n FROM experiments WHERE state != 'planned'").fetchone()["n"]

    def mark_started(self, eid: str, adapter_kind: str | None, adapter_sha: str | None, fidelity: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE experiments SET started_at=?, state='running', adapter_kind=?, adapter_sha256=?, "
                      "adapter_fidelity=? WHERE id=?", (utcnow(), adapter_kind, adapter_sha, fidelity, eid))
            self._event(c, "experiment", eid, "started", {"adapter_sha256": adapter_sha, "fidelity": fidelity})

    def mark_finished(self, eid: str, result: dict | None, artifacts: list[dict], error: str | None) -> None:
        res_txt = canonical(result) if result is not None else None
        sha = text_sha256(res_txt) if res_txt is not None else None
        state = "done" if error is None else "failed"
        with self._conn() as c:
            c.execute("UPDATE experiments SET finished_at=?, state=?, result=?, result_sha256=?, artifacts=?, "
                      "error=? WHERE id=?", (utcnow(), state, res_txt, sha, canonical(artifacts), error, eid))
            self._event(c, "experiment", eid, "finished",
                        {"state": state, "result_sha256": sha, "artifacts": artifacts, "error": error})
