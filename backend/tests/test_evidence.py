"""Evidence: two-track call recording with SHA-256, an evidence pack per call, and a mule-ID feed for banks."""

import csv
import hashlib
import io
import json
import wave
import zipfile

import numpy as np

from voice_core.types import Turn

from dadi.evidence import CallRecorder, build_evidence_pack, feed_csv, mule_feed
from dadi.store import Store

SR = 8000


def _tone(seconds: float, amp: int = 5000) -> bytes:
    return np.full(int(SR * seconds), amp, "<i2").tobytes()


def _channels(wav: bytes) -> tuple[np.ndarray, np.ndarray]:
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getnchannels() == 2 and w.getframerate() == SR and w.getsampwidth() == 2
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2)
    return x[:, 0], x[:, 1]


def test_tracks_are_time_aligned_and_bursts_queue_like_playback():
    r = CallRecorder(SR)
    for i in range(20):  # 2 s of caller audio in 0.1 s frames, arriving in real time
        r.caller(_tone(0.1, 1000), t=(i + 1) * 0.1)
    r.agent(_tone(0.5), t=1.0)  # TTS chunks arrive faster than they play...
    r.agent(_tone(0.5), t=1.01)  # ...so the second one starts when the first ends
    left, right = _channels(r.wav())
    assert len(left) == len(right) == 2 * SR
    assert (left[: 2 * SR] == 1000).all()
    assert (right[:SR] == 0).all() and (right[SR : 2 * SR] == 5000).all()
    assert abs(r.seconds - 2.0) < 1e-6


def test_barge_in_cuts_dadi_where_playback_stopped():
    r = CallRecorder(SR)
    r.agent(_tone(2.0), t=1.0)  # 2 s reply sent in one burst at t=1
    r.stop_agent(t=1.5)  # the scammer interrupted at t=1.5: the rest never played
    r.agent(_tone(0.25, 3000), t=2.0)
    _, right = _channels(r.wav())
    assert (right[SR : int(1.5 * SR)] == 5000).all()
    assert (right[int(1.5 * SR) : 2 * SR] == 0).all()
    assert (right[2 * SR : int(2.25 * SR)] == 3000).all()


def test_recording_is_capped():
    r = CallRecorder(SR, max_seconds=1.0)
    r.caller(_tone(3.0), t=3.0)
    r.agent(_tone(3.0), t=0.0)
    left, right = _channels(r.wav())
    assert len(left) == SR and r.seconds == 1.0


def test_empty_recording_has_no_wav():
    assert CallRecorder(SR).wav() is None


def test_save_writes_wav_with_matching_sha256(tmp_path):
    r = CallRecorder(SR)
    r.caller(_tone(1.0), t=1.0)
    meta = r.save(tmp_path / "rec", "call1")
    data = (tmp_path / "rec" / "call1.wav").read_bytes()
    assert meta["sha256"] == hashlib.sha256(data).hexdigest() and meta["bytes"] == len(data)
    assert meta["seconds"] == 1.0
    s = Store(tmp_path / "d.db")
    s.save_recording("call1", meta)
    got = s.recording("call1")
    assert got["sha256"] == meta["sha256"] and got["path"].endswith("call1.wav")
    assert s.recording("nope") is None


def test_evidence_pack_manifest_hashes_every_file():
    turns = [Turn("scammer", "UPI ID likhiye: rathore.cbi@okaxis", 3.0), Turn("dadi", "हाँ बेटा, लिख रही हूँ।", 5.5)]
    report = {"call_id": "c1", "summary": "test", "suspect_identifiers": {"upi_ids": ["rathore.cbi@okaxis"]}}
    wav = CallRecorder(SR)
    wav.caller(_tone(1.0), t=1.0)
    pack = build_evidence_pack(report, turns, wav.wav(), {"sha256": "abc", "seconds": 1.0})
    z = zipfile.ZipFile(io.BytesIO(pack))
    assert set(z.namelist()) == {"manifest.json", "report.json", "transcript.txt", "recording.wav"}
    man = json.loads(z.read("manifest.json"))
    for f in man["files"]:
        assert hashlib.sha256(z.read(f["name"])).hexdigest() == f["sha256"]
    assert man["call_id"] == "c1" and "review" in man["note"].lower()
    text = z.read("transcript.txt").decode("utf-8")
    assert "[0:03] Scammer: UPI ID likhiye: rathore.cbi@okaxis" in text and "[0:05] Dadi: हाँ बेटा" in text
    no_audio = zipfile.ZipFile(io.BytesIO(build_evidence_pack(report, turns, None, None)))
    assert "recording.wav" not in no_audio.namelist()


def test_mule_feed_groups_identifiers_across_calls():
    calls = [
        {"id": "c1", "started_at": 100.0, "intel": {"upi_ids": ["rathore.cbi@okaxis"], "names": ["Vijay Rathore"],
                                                    "scam_type": "digital_arrest", "phones": ["9876543210"]}},
        {"id": "c2", "started_at": 300.0, "intel": {"upi_ids": ["RATHORE.CBI@okaxis"], "names": ["Rahul"],
                                                    "scam_type": "kyc_bank_block"}},
        {"id": "c3", "started_at": 200.0, "intel": {}},
    ]
    rows = mule_feed(calls, ring_of={"c1": 1, "c2": 1})
    upi = next(r for r in rows if r["kind"] == "upi_id")
    assert upi["value"] == "rathore.cbi@okaxis" and upi["calls"] == 2 and upi["call_ids"] == ["c1", "c2"]
    assert upi["first_seen"] == 100.0 and upi["last_seen"] == 300.0
    assert upi["aliases"] == ["Rahul", "Vijay Rathore"] and upi["scam_types"] == ["digital_arrest", "kyc_bank_block"]
    assert upi["ring"] == 1 and rows[0] is upi  # most-seen first
    phone = next(r for r in rows if r["kind"] == "phone")
    assert phone["calls"] == 1
    out = list(csv.DictReader(io.StringIO(feed_csv(rows))))
    assert out[0]["value"] == "rathore.cbi@okaxis" and out[0]["call_ids"] == "c1;c2"
    assert out[0]["first_seen"].startswith("1970-01-01T00:01:40")
