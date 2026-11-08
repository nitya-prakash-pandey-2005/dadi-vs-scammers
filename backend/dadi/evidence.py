"""Evidence for police and banks.

- `CallRecorder`: a two-track recording of each live call (left = caller as received, right = Dadi as actually
  played), time-aligned on the call clock. TTS chunks arrive faster than they play, so Dadi's track is laid out like
  the caller's player does; a barge-in cuts it where playback stopped. Saved as a stereo WAV with its SHA-256, so
  anyone can check later that the file was not changed.
- `build_evidence_pack`: one ZIP per call (report, full transcript, recording, manifest with a SHA-256 per file).
- `mule_feed` / `feed_csv`: every mule identifier across all calls, grouped (first/last seen, calls, aliases, scam
  types, ring), in a shape a bank's fraud team or I4C can ingest.

The demo uses synthetic calls only. Recording law is the deployer's job: Dadi is a party to the call, and the
recordings stay on the server that took the call (`cache/recordings/`, git-ignored).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import wave
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from voice_core.types import Turn

from .report import DISCLAIMER

FEED_KINDS = {"upi_ids": "upi_id", "phones": "phone", "accounts": "bank_account", "ifsc": "ifsc", "urls": "url"}
FEED_COLUMNS = ["kind", "value", "calls", "first_seen", "last_seen", "scam_types", "aliases", "ring", "call_ids"]


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat() if ts else None


def _mmss(sec: float) -> str:
    sec = int(sec or 0)
    return f"{sec // 60}:{sec % 60:02d}"


class CallRecorder:
    def __init__(self, sample_rate: int, max_seconds: float = 900.0):
        self.sr = sample_rate
        self._max = int(max_seconds * sample_rate) * 2  # bytes per track
        self._caller = bytearray()
        self._agent = bytearray()
        self._caller_end = 0  # bytes
        self._agent_end = 0

    def _write(self, track: bytearray, pos: int, pcm16: bytes) -> int:
        pos -= pos % 2
        if pos >= self._max or not pcm16:
            return pos
        pcm16 = pcm16[: self._max - pos]
        if len(track) < pos:
            track.extend(b"\x00" * (pos - len(track)))
        track[pos : pos + len(pcm16)] = pcm16
        return pos + len(pcm16)

    def caller(self, pcm16: bytes, t: float) -> None:
        """A mic frame that arrived `t` seconds into the call (it ends at t)."""
        start = max(self._caller_end, int(t * self.sr) * 2 - len(pcm16))
        self._caller_end = self._write(self._caller, start, pcm16)

    def agent(self, pcm16: bytes, t: float) -> None:
        """Agent audio sent at `t`; it plays after whatever is still queued at the caller's end."""
        start = max(self._agent_end, int(t * self.sr) * 2)
        self._agent_end = self._write(self._agent, start, pcm16)

    def stop_agent(self, t: float) -> None:
        """Barge-in: the caller's player was flushed at `t`; queued agent audio after that never played."""
        cut = min(len(self._agent), int(t * self.sr) * 2)
        del self._agent[cut:]
        self._agent_end = min(self._agent_end, cut)

    @property
    def seconds(self) -> float:
        return max(len(self._caller), len(self._agent)) / 2 / self.sr

    def wav(self) -> bytes | None:
        n = max(len(self._caller), len(self._agent)) // 2
        if not n:
            return None
        st = np.zeros((n, 2), "<i2")
        left = np.frombuffer(bytes(self._caller[: len(self._caller) // 2 * 2]), "<i2")
        right = np.frombuffer(bytes(self._agent[: len(self._agent) // 2 * 2]), "<i2")
        st[: len(left), 0] = left
        st[: len(right), 1] = right
        bio = io.BytesIO()
        with wave.open(bio, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(self.sr)
            w.writeframes(st.tobytes())
        return bio.getvalue()

    def save(self, directory: Path | str, call_id: str) -> dict | None:
        data = self.wav()
        if data is None:
            return None
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{call_id}.wav"
        path.write_bytes(data)
        return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                "seconds": round(self.seconds, 2), "channels": {"left": "caller", "right": "dadi"}}


def transcript_text(turns: list[Turn], agent_name: str = "Dadi") -> str:
    who = {"scammer": "Scammer"}
    return "\n".join(f"[{_mmss(t.t)}] {who.get(t.speaker, agent_name)}: {t.text}" for t in turns) + "\n"


def build_evidence_pack(report: dict, turns: list[Turn], recording_wav: bytes | None, recording_meta: dict | None) -> bytes:
    files: list[tuple[str, bytes]] = [
        ("report.json", json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")),
        ("transcript.txt", transcript_text(turns).encode("utf-8")),
    ]
    if recording_wav:
        files.append(("recording.wav", recording_wav))
    manifest = {
        "call_id": report.get("call_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "Dadi vs Scammers (Gnani Prisma + Timbre)",
        "note": DISCLAIMER + " Check each file against its SHA-256 below before relying on it.",
        "recording": {k: v for k, v in (recording_meta or {}).items() if k != "path"} or None,
        "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files],
    }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for name, data in files:
            z.writestr(name, data)
    return bio.getvalue()


def mule_feed(calls: list[dict], ring_of: dict[str, int] | None = None) -> list[dict]:
    """calls: [{id, started_at, intel}] -> one row per (kind, value), most-seen first."""
    ring_of = ring_of or {}
    rows: dict[tuple[str, str], dict] = {}
    for c in sorted(calls, key=lambda c: c.get("started_at") or 0):
        intel = c.get("intel") or {}
        for field, kind in FEED_KINDS.items():
            for v in intel.get(field) or []:
                key = (kind, str(v).strip().lower())
                r = rows.setdefault(key, {"kind": kind, "value": key[1], "call_ids": [], "aliases": set(),
                                          "scam_types": set(), "first_seen": c.get("started_at"), "ring": None})
                if c["id"] not in r["call_ids"]:
                    r["call_ids"].append(c["id"])
                r["last_seen"] = c.get("started_at")
                r["aliases"].update(intel.get("names") or [])
                if intel.get("scam_type") and intel["scam_type"] != "other":
                    r["scam_types"].add(intel["scam_type"])
                r["ring"] = r["ring"] or ring_of.get(c["id"])
    out = []
    for r in rows.values():
        r["calls"] = len(r["call_ids"])
        r["aliases"], r["scam_types"] = sorted(r["aliases"]), sorted(r["scam_types"])
        out.append(r)
    out.sort(key=lambda r: (-r["calls"], -(r["last_seen"] or 0)))
    return out


def feed_csv(rows: list[dict]) -> str:
    bio = io.StringIO()
    w = csv.DictWriter(bio, fieldnames=FEED_COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({**r, "first_seen": _iso(r.get("first_seen")), "last_seen": _iso(r.get("last_seen")),
                    "scam_types": ";".join(r["scam_types"]), "aliases": ";".join(r["aliases"]),
                    "call_ids": ";".join(r["call_ids"]), "ring": r.get("ring") or ""})
    return bio.getvalue()
