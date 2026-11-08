"""SQLite persistence for calls, turns and intel."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

import numpy as np

from voice_core.types import Turn

from .intel import IntelReport

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
  id TEXT PRIMARY KEY, persona TEXT, started_at REAL, ended_at REAL,
  wasted_seconds REAL DEFAULT 0, intel TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT, call_id TEXT, speaker TEXT, text TEXT,
  t REAL, lang TEXT, latency_ms REAL
);
CREATE INDEX IF NOT EXISTS turns_call ON turns(call_id);
CREATE TABLE IF NOT EXISTS voiceprints (call_id TEXT PRIMARY KEY, vec BLOB);
CREATE TABLE IF NOT EXISTS recordings (call_id TEXT PRIMARY KEY, meta TEXT);
"""


class Store:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def create_call(self, persona: str) -> str:
        cid = uuid.uuid4().hex[:12]
        self.db.execute("INSERT INTO calls(id, persona, started_at) VALUES (?,?,?)", (cid, persona, time.time()))
        self.db.commit()
        return cid

    def set_persona(self, call_id: str, persona: str) -> None:
        self.db.execute("UPDATE calls SET persona=? WHERE id=?", (persona, call_id))
        self.db.commit()

    def add_turn(self, call_id: str, turn: Turn) -> None:
        self.db.execute(
            "INSERT INTO turns(call_id, speaker, text, t, lang, latency_ms) VALUES (?,?,?,?,?,?)",
            (call_id, turn.speaker, turn.text, turn.t, turn.lang, turn.latency_ms),
        )
        self.db.commit()

    def save_intel(self, call_id: str, intel: IntelReport) -> None:
        self.db.execute("UPDATE calls SET intel=? WHERE id=?", (intel.model_dump_json(), call_id))
        self.db.commit()

    def end_call(self, call_id: str, wasted_seconds: float) -> None:
        self.db.execute("UPDATE calls SET ended_at=?, wasted_seconds=? WHERE id=?",
                        (time.time(), float(wasted_seconds), call_id))
        self.db.commit()

    def _call_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["intel"] = json.loads(d.get("intel") or "{}")
        return d

    def get_call(self, call_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
        if not row:
            return None
        d = self._call_dict(row)
        d["turns"] = [dict(r) for r in self.db.execute(
            "SELECT speaker, text, t, lang, latency_ms FROM turns WHERE call_id=? ORDER BY id", (call_id,))]
        return d

    def list_calls(self, limit: int = 50) -> list[dict]:
        rows = self.db.execute("SELECT * FROM calls ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._call_dict(r) for r in rows]

    def totals(self) -> dict:
        rows = self.db.execute("SELECT wasted_seconds, intel FROM calls").fetchall()
        mule: set[str] = set()
        seconds = 0.0
        for r in rows:
            seconds += float(r["wasted_seconds"] or 0)
            intel = json.loads(r["intel"] or "{}")
            for k in ("upi_ids", "accounts", "phones"):
                mule.update(str(x).lower() for x in intel.get(k, []))
        return {"calls": len(rows), "seconds_wasted": seconds, "mule_ids": len(mule)}

    def save_voiceprint(self, call_id: str, vec: np.ndarray) -> None:
        self.db.execute("INSERT OR REPLACE INTO voiceprints(call_id, vec) VALUES (?,?)",
                        (call_id, np.asarray(vec, "<f4").tobytes()))
        self.db.commit()

    def voiceprints(self) -> dict[str, np.ndarray]:
        return {r["call_id"]: np.frombuffer(r["vec"], "<f4") for r in self.db.execute("SELECT * FROM voiceprints")}

    def save_recording(self, call_id: str, meta: dict) -> None:
        self.db.execute("INSERT OR REPLACE INTO recordings(call_id, meta) VALUES (?,?)", (call_id, json.dumps(meta)))
        self.db.commit()

    def recording(self, call_id: str) -> dict | None:
        row = self.db.execute("SELECT meta FROM recordings WHERE call_id=?", (call_id,)).fetchone()
        return json.loads(row["meta"]) if row else None
