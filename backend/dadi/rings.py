"""Scam Ring Radar: links calls that share a mule ID (UPI, phone, account) or the same scammer voice.

The voice fingerprint is Gnani's voice-clone speaker embedding (768-d). Live checks, 8 Nov, 8 kHz phone band:
same voice, same line conditions 0.93-0.96; different clean Timbre voices up to 0.777 (Shubham/Yashraj);
same voice across clean vs 10 dB-noise conditions only 0.76-0.80, but still the top match (6/6).
"""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

VOICE_MATCH = 0.85
SYNTH_FLOOR, SYNTH_MARGIN = 0.75, 0.05
ID_KINDS = {"upi_ids": "UPI", "phones": "phone", "accounts": "account"}


def voiceprint_vec(embedding: dict) -> np.ndarray:
    return np.frombuffer(base64.b64decode(embedding["embedding"]), "<f4").astype(np.float32)


def speech_only(pcm16: bytes, sr: int, *, frame_ms: int = 30, max_s: float = 25.0) -> bytes:
    """Keeps the loud frames (speech), drops silence, caps the length for the embedding endpoint (5-30 s)."""
    x = np.frombuffer(pcm16[: len(pcm16) // 2 * 2], "<i2")
    n = sr * frame_ms // 1000
    frames = x[: len(x) // n * n].reshape(-1, n) if len(x) >= n else x.reshape(0, n)
    if not len(frames):
        return b""
    rms = np.sqrt((frames.astype(np.float32) ** 2).mean(1))
    keep = frames[rms > max(300.0, 0.25 * float(np.percentile(rms, 90)))]
    return keep.reshape(-1)[: int(max_s * sr)].astype("<i2").tobytes()


@lru_cache(maxsize=1)
def tts_catalog() -> dict[str, np.ndarray]:
    """Fingerprints of the 13 Timbre v3.0 voices (scripts/build_tts_voiceprints.py)."""
    data = json.loads((Path(__file__).parent / "data" / "tts_voiceprints.json").read_text())
    return {k: np.frombuffer(base64.b64decode(b), "<f4") for k, b in data["voices"].items()}


def synthetic_voice(vec: np.ndarray, catalog: dict[str, np.ndarray]) -> dict | None:
    """A known TTS voice that is clearly the closest match, else None. Catalogue match only, not deepfake detection."""
    ranked = sorted(((_cos(vec, v), k) for k, v in catalog.items()), reverse=True)
    if len(ranked) < 2 or ranked[0][0] < SYNTH_FLOOR or ranked[0][0] - ranked[1][0] < SYNTH_MARGIN:
        return None
    return {"voice": ranked[0][1], "score": round(ranked[0][0], 3)}


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def build_rings(calls: list[dict], prints: dict[str, np.ndarray], threshold: float = VOICE_MATCH,
                catalog: dict[str, np.ndarray] | None = None) -> dict:
    """calls: [{id, intel}] -> {nodes, links: [{source, target, reason, kind}], rings: [{calls, aliases, ids, scam_types}]}."""
    ids = {c["id"]: {(k, str(v).lower()) for k in ID_KINDS for v in (c.get("intel") or {}).get(k, [])} for c in calls}
    links = []
    for i, a in enumerate(calls):
        for b in calls[i + 1:]:
            shared = sorted(ids[a["id"]] & ids[b["id"]])
            if shared:
                k, v = shared[0]
                links.append({"source": a["id"], "target": b["id"], "kind": "id", "reason": f"same {ID_KINDS[k]} {v}"})
            elif a["id"] in prints and b["id"] in prints:
                s = _cos(prints[a["id"]], prints[b["id"]])
                if s >= threshold:
                    links.append({"source": a["id"], "target": b["id"], "kind": "voice", "reason": f"same voice ({s:.2f})"})

    parent = {c["id"]: c["id"] for c in calls}

    def root(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for l in links:
        parent[root(l["source"])] = root(l["target"])
    groups: dict[str, list[dict]] = {}
    for c in calls:
        groups.setdefault(root(c["id"]), []).append(c)
    rings = []
    for members in groups.values():
        if len(members) < 2:
            continue
        intel = [m.get("intel") or {} for m in members]
        rings.append({
            "calls": [m["id"] for m in members],
            "aliases": sorted({n for i in intel for n in i.get("names", [])}),
            "ids": sorted({v for m in members for _, v in ids[m["id"]]}),
            "scam_types": sorted({i.get("scam_type") for i in intel if i.get("scam_type")}),
        })
    rings.sort(key=lambda r: -len(r["calls"]))
    ring_of = {cid: n for n, r in enumerate(rings, 1) for cid in r["calls"]}
    nodes = [{"id": c["id"], "ring": ring_of.get(c["id"]), "voiceprint": c["id"] in prints,
              "synthetic": synthetic_voice(prints[c["id"]], catalog) if catalog and c["id"] in prints else None,
              "names": (c.get("intel") or {}).get("names", []), "scam_type": (c.get("intel") or {}).get("scam_type"),
              "ids": sorted(v for _, v in ids[c["id"]])} for c in calls]
    return {"nodes": nodes, "links": links, "rings": rings}
