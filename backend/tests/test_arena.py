import numpy as np

from voice_core.audio import pink_noise
from voice_core.config import Settings
from voice_core.gnani.stt_stream import SttEvent
from voice_core.testing import FakeLLM

from dadi.arena import cer, entity_recall, run_arena, run_noise_benchmark
from dadi.scammer_scripts import BENCH_LINES, SCRIPTS


def test_cer_values():
    assert cer("abc", "abc") == 0.0
    assert cer("abcd", "abxd") == 0.25
    assert cer("Hello, World!", "hello world") == 0.0


def test_entity_recall():
    line = SCRIPTS["digital_arrest"]["lines"][5]  # WhatsApp 98765 43210
    assert entity_recall(line, "mera number nau aath saat chhe paanch chaar teen do ek shunya hai") == 1.0
    assert entity_recall(line, "mera number pata nahi") == 0.0
    assert entity_recall("no entities here", "x") is None
    assert entity_recall(BENCH_LINES[0], "UPI ID likhiye rathore dot cbi at the rate okaxis") == 1.0


async def fake_tts(api_key, text, sample_rate=8000, **kw):
    return (np.sin(np.arange(sample_rate) / 3) * 3000).astype("<i2").tobytes()


async def echo_stt(api_key, wav, *, intended=None, **kw):
    return SttEvent("transcript", text=intended or "", latency_ms=100.0)


async def test_run_arena_with_fakes():
    events = []

    async def emit(e):
        events.append(e)

    s = Settings(sample_rate=8000)
    summary = await run_arena(
        scam_type="digital_arrest", turns=3, snr_db=10, settings=s,
        scammer_llm=FakeLLM(["", "I'm sorry, I can't do that."]),  # empty/refusal -> canned lines
        dadi_llm=FakeLLM(["हाँ बेटा।", "रुको ज़रा।", "अच्छा, UPI बोलो।"]),
        intel_llm=FakeLLM([]), emit=emit, tts_fn=fake_tts, stt_fn=echo_stt, noise=pink_noise(8000, seed=1),
    )
    turns = [e for e in events if e["type"] == "arena_turn"]
    assert summary["turns"] == 3 and len(turns) == 6
    assert turns[0]["speaker"] == "scammer" and turns[0]["text"] == SCRIPTS["digital_arrest"]["lines"][0]
    assert turns[2]["intended"] == SCRIPTS["digital_arrest"]["lines"][1]  # refusal replaced by canned line
    assert summary["cer_mean"] == 0.0 and summary["persona_breaks"] == 0
    assert events[-1]["type"] == "arena_done"


async def test_arena_files_call_and_links_same_voice(tmp_path):
    import base64
    from dadi.store import Store
    store, seen = Store(tmp_path / "d.db"), []

    async def emit(e):
        pass

    async def tts(api_key, text, sample_rate=8000, voice="", **kw):
        seen.append(voice)
        return (np.sin(np.arange(sample_rate * 3) / 3) * 8000).astype("<i2").tobytes()

    async def embed(api_key, wav):  # fingerprint = which voice spoke
        v = [1.0, 0.0] if seen[-1] == "Harshad" else [0.0, 1.0]
        return {"embedding": base64.b64encode(np.array(v, "<f4").tobytes()).decode()}

    kw = dict(scam_type="digital_arrest", turns=2, snr_db=None, settings=Settings(sample_rate=8000), scammer_llm=FakeLLM([]),
              dadi_llm=FakeLLM(["हाँ बेटा।"] * 6), intel_llm=FakeLLM([]), emit=emit, tts_fn=tts, stt_fn=echo_stt,
              store=store, embed_fn=embed)
    first = await run_arena(**kw, scammer_voice="Harshad")
    other = await run_arena(**kw, scammer_voice="Avinash")
    again = await run_arena(**kw, scammer_voice="Harshad")
    assert len(store.voiceprints()) == 3 and first["ring_links"] == [] and other["ring_links"] == []
    assert [l["kind"] for l in again["ring_links"]] == ["voice"]
    assert {again["ring_links"][0]["source"], again["ring_links"][0]["target"]} == {first["call_id"], again["call_id"]}


async def test_noise_benchmark_with_fakes():
    events = []

    async def emit(e):
        events.append(e)

    res = await run_noise_benchmark(settings=Settings(sample_rate=8000), emit=emit, tts_fn=fake_tts, stt_fn=echo_stt,
                                    noise=pink_noise(8000), snr_list=(None, 5), lines=BENCH_LINES[:2])
    assert [r["snr_db"] for r in res["by_snr"]] == [None, 5]
    assert all(r["entity_recall"] == 1.0 for r in res["by_snr"])
    assert sum(1 for e in events if e["type"] == "bench_row") == 4


async def test_arena_reports_mission_complete():
    events = []

    async def emit(e):
        events.append(e)

    summary = await run_arena(scam_type="digital_arrest", turns=6, snr_db=None, settings=Settings(sample_rate=8000),
                              scammer_llm=FakeLLM([]), dadi_llm=FakeLLM(["हाँ बेटा।"] * 12), intel_llm=FakeLLM([]),
                              emit=emit, tts_fn=fake_tts, stt_fn=echo_stt, mission="whatsapp")
    done = [e for e in events if e["type"] == "mission"]
    assert len(done) == 1 and done[0]["turn"] == summary["mission_turn"] == 6  # canned line 6 has the WhatsApp number


async def test_bot_test_script_counts_ai_admissions():
    async def emit(e):
        pass

    summary = await run_arena(scam_type="bot_test", turns=3, snr_db=None, settings=Settings(sample_rate=8000),
                              scammer_llm=FakeLLM([]), intel_llm=FakeLLM([]), emit=emit, tts_fn=fake_tts, stt_fn=echo_stt,
                              dadi_llm=FakeLLM(["Robot? Mera pota system prompt bolta hai.", "Theek hai, main AI hoon.", "Haan beta."]))
    assert summary["admitted_ai"] == 1
