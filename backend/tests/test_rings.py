import base64

import numpy as np

from dadi.rings import build_rings, speech_only, voiceprint_vec
from dadi.store import Store


def _emb(v):
    return {"embedding": base64.b64encode(np.asarray(v, "<f4").tobytes()).decode(), "shape": [1, len(v)]}


def test_voiceprint_vec_decodes_gnani_base64():
    assert np.allclose(voiceprint_vec(_emb([0.5, -1.0, 2.0])), [0.5, -1.0, 2.0])


def test_speech_only_drops_silence_and_caps_length():
    sr = 8000
    loud = (np.sin(np.arange(sr) / 3) * 8000).astype("<i2")
    pcm = np.concatenate([np.zeros(sr, "<i2"), loud, np.zeros(sr, "<i2"), loud]).tobytes()
    out = speech_only(pcm, sr)
    assert abs(len(out) / 2 / sr - 2.0) < 0.1
    assert len(speech_only(pcm, sr, max_s=1.5)) / 2 / sr <= 1.5


def test_build_rings_links_by_mule_id_and_by_voice():
    a, b, c = np.array([1.0, 0, 0]), np.array([0.95, 0.3, 0]), np.array([0, 1.0, 0])  # a~b same voice
    calls = [
        {"id": "c1", "intel": {"upi_ids": ["rathore.cbi@okaxis"], "names": ["Vijay Rathore"], "scam_type": "digital_arrest"}},
        {"id": "c2", "intel": {"phones": ["9876543210"], "names": ["Sharma"], "scam_type": "kyc_update"}},
        {"id": "c3", "intel": {"upi_ids": ["RATHORE.CBI@okaxis"], "scam_type": "digital_arrest"}},
        {"id": "c4", "intel": {"upi_ids": ["someone@ybl"]}},
    ]
    r = build_rings(calls, {"c1": a, "c2": b, "c4": c})
    reasons = {(l["source"], l["target"]): l["reason"] for l in r["links"]}
    assert reasons[("c1", "c2")].startswith("same voice")
    assert reasons[("c1", "c3")] == "same UPI rathore.cbi@okaxis"
    assert ("c1", "c4") not in reasons and ("c2", "c4") not in reasons
    assert r["rings"][0]["calls"] == ["c1", "c2", "c3"] and r["rings"][0]["aliases"] == ["Sharma", "Vijay Rathore"]
    assert all(ring["calls"] != ["c4"] for ring in r["rings"])  # a lone call is not a ring


def test_store_keeps_voiceprints(tmp_path):
    s = Store(tmp_path / "d.db")
    cid = s.create_call("dadi")
    s.save_voiceprint(cid, np.array([0.1, 0.2], "<f4"))
    assert np.allclose(s.voiceprints()[cid], [0.1, 0.2])
