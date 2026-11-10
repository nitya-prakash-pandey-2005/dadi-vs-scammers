"""Dadi never forgets a voice: live repeat-caller detection from Gnani voice-clone embeddings."""

import base64

import numpy as np

from voice_core.testing import FakeLLM
from voice_core.types import Turn

from dadi.agent import DadiAgent
from dadi.intel import IntelReport
from dadi.store import Store
from dadi.voicewatch import VoiceWatch, best_match

SR = 8000


def _emb(v):
    return {"embedding": base64.b64encode(np.asarray(v, "<f4").tobytes()).decode(), "shape": [1, len(v)]}


def _speech(seconds: float) -> bytes:
    return (np.sin(np.arange(int(SR * seconds)) / 3) * 8000).astype("<i2").tobytes()


def _frames(pcm: bytes, n: int = 1024):
    return [pcm[i : i + n] for i in range(0, len(pcm), n)]


def _old_call(store: Store, vec, names=("Vijay Rathore",), scam_type="digital_arrest") -> str:
    cid = store.create_call("dadi")
    store.save_intel(cid, IntelReport(names=list(names), scam_type=scam_type, upi_ids=["rathore.cbi@okaxis"]))
    store.end_call(cid, 300)
    store.save_voiceprint(cid, np.asarray(vec, "<f4"))
    return cid


class Embedder:
    def __init__(self, vec, fail=False):
        self.vec, self.fail, self.calls = vec, fail, 0

    async def __call__(self, api_key, wav):
        self.calls += 1
        if self.fail:
            raise RuntimeError("gnani down")
        return _emb(self.vec)


def test_best_match_picks_closest_above_threshold_and_skips_self():
    prints = {"a": np.array([1.0, 0, 0]), "b": np.array([0.9, 0.1, 0]), "me": np.array([1.0, 0, 0])}
    hit = best_match(np.array([1.0, 0, 0]), prints, exclude="me")
    assert hit[0] == "a" and abs(hit[1] - 1.0) < 1e-6
    assert best_match(np.array([0, 0, 1.0]), prints, exclude="me") is None
    assert best_match(np.array([1.0, 0, 0]), {}, exclude=None) is None


async def test_live_match_fires_once_with_the_earlier_calls_alias(tmp_path):
    store = Store(tmp_path / "d.db")
    old = _old_call(store, [1.0, 0, 0])
    cid = store.create_call("dadi")
    got = []

    async def on_match(m):
        got.append(m)

    emb = Embedder([0.99, 0.05, 0])
    w = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=emb, api_key="K", on_match=on_match)
    for f in _frames(_speech(12)):
        w.feed(f)
    await w.wait()
    assert emb.calls == 1 and len(got) == 1
    m = got[0]
    assert m["call_id"] == old and m["similarity"] > 0.95 and m["names"] == ["Vijay Rathore"]
    assert m["scam_type"] == "digital_arrest" and "rathore.cbi@okaxis" in m["ids"]


async def test_silence_never_triggers_and_unknown_voice_does_not_match(tmp_path):
    store = Store(tmp_path / "d.db")
    _old_call(store, [1.0, 0, 0])
    cid = store.create_call("dadi")
    got = []

    async def on_match(m):
        got.append(m)

    emb = Embedder([0, 1.0, 0])
    w = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=emb, api_key="K", on_match=on_match)
    for f in _frames(b"\x00\x00" * SR * 20):
        w.feed(f)
    await w.wait()
    assert emb.calls == 0
    for f in _frames(_speech(10)):
        w.feed(f)
    await w.wait()
    assert emb.calls == 1 and got == []


async def test_finish_saves_the_voiceprint_and_reuses_the_live_one(tmp_path):
    store = Store(tmp_path / "d.db")
    cid = store.create_call("dadi")
    emb = Embedder([0.0, 0.0, 1.0])

    async def on_match(m):
        pass

    w = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=emb, api_key="K", on_match=on_match)
    for f in _frames(_speech(9)):
        w.feed(f)
    await w.finish()
    assert emb.calls == 1  # 9 s total: the live fingerprint is good enough, no second Gnani call
    assert np.allclose(store.voiceprints()[cid], [0, 0, 1.0])


async def test_finish_refingerprints_when_much_more_speech_arrived(tmp_path):
    store = Store(tmp_path / "d.db")
    cid = store.create_call("dadi")
    emb = Embedder([0.0, 1.0, 0.0])

    async def on_match(m):
        pass

    w = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=emb, api_key="K", on_match=on_match)
    for f in _frames(_speech(30)):
        w.feed(f)
    await w.finish()
    assert emb.calls == 2 and cid in store.voiceprints()


async def test_embed_failure_is_harmless(tmp_path):
    store = Store(tmp_path / "d.db")
    cid = store.create_call("dadi")

    async def on_match(m):
        raise AssertionError("no match expected")

    w = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=Embedder([1.0], fail=True), api_key="K",
                   on_match=on_match)
    for f in _frames(_speech(12)):
        w.feed(f)
    await w.finish()
    assert store.voiceprints() == {}


async def test_short_call_and_no_embedder_save_nothing(tmp_path):
    store = Store(tmp_path / "d.db")
    cid = store.create_call("dadi")

    async def on_match(m):
        pass

    w = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=Embedder([1.0]), api_key="K", on_match=on_match)
    for f in _frames(_speech(3)):
        w.feed(f)
    await w.finish()
    w2 = VoiceWatch(store=store, call_id=cid, sample_rate=SR, embed_fn=None, api_key="K", on_match=on_match)
    for f in _frames(_speech(12)):
        w2.feed(f)
    await w2.finish()
    assert store.voiceprints() == {}


async def test_agent_recognise_teases_once_then_stays_aware(tmp_path):
    store = Store(tmp_path / "d.db")
    llm = FakeLLM(["अरे बेटा, तुम्हारी आवाज़ तो पहचानी हुई है।", "हाँ बेटा।", "अच्छा।"])
    agent = DadiAgent(store=store, llm=llm, intel_llm=FakeLLM([]), persona_key="dadi", seed=1)
    evt = agent.recognise({"call_id": "c0", "similarity": 0.93, "names": ["Vijay Rathore"],
                           "scam_type": "digital_arrest", "ids": ["rathore.cbi@okaxis"], "started_at": 0})
    assert evt["type"] == "repeat_caller" and evt["call_id"] == agent.call_id and evt["match"]["call_id"] == "c0"
    hist = [Turn("scammer", "Main SBI se bol raha hoon", 1.0)]
    for _ in range(2):
        _ = [s async for s in agent.reply_sentences(hist)]
    first, second = llm.calls[0][0]["content"], llm.calls[1][0]["content"]
    assert "recognise this man's voice" in first and "Vijay Rathore" in first
    assert "recognise this man's voice" not in second and "already told him" in second
    assert agent.turn_meta().get("recognised") is True
