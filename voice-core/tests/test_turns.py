import asyncio
import random

from voice_core.config import Settings
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeStt, ev, fake_tts
from voice_core.turns import split_sentences


def test_split_sentences_final_flush():
    assert split_sentences("एक। दो", final=True) == (["एक।", "दो"], "")
    assert split_sentences("no end yet") == ([], "no end yet")


class _Agent:
    user_label, agent_label = "user", "agent"
    voice, tts_language, speed = "Lakshmi", "hi-IN", 1.0
    stt_language_code, keyterms = "hi-IN", []

    def greeting(self):
        return ""

    def filler_texts(self):
        return []

    def on_language(self, code):
        return None

    async def reply_sentences(self, history):
        yield "ठीक है।"

    async def on_user_turn(self, history):
        return None

    async def record(self, turn):
        pass


async def test_tts_waits_for_turn_based_stt_lock():
    stt = FakeStt([ev("transcript", "namaste ji")], gap=0.01)
    stt.busy = asyncio.Lock()
    await stt.busy.acquire()  # a REST transcription is "in flight"
    audio = []

    async def sj(m):
        pass

    async def sa(b):
        audio.append(b)

    s = VoiceAgentSession(_Agent(), send_json=sj, send_audio=sa, settings=Settings(), stt_factory=lambda: stt,
                          tts_fn=fake_tts, rng=random.Random(0))
    await s.start()
    await asyncio.sleep(0.1)
    assert audio == []  # blocked while STT is busy
    stt.busy.release()
    await s.wait_idle()
    assert len(audio) == 2
    await s.hangup()


def test_is_echo_ignores_spelling_variants_and_spans_lines():
    from voice_core.turns import is_echo

    agent = ["हाँ बेटा… <coughs> एक मिनट…", "हाँ बेटा…", "<coughs> रुको ज़रा…", "अभी चश्मा ढूँढ के बताती हूँ।"]
    assert is_echo("हां बेटा रुको जरा अभी चश्मा ढूंढ के बताती हूं", agent)  # anusvara / no nukta, 3 lines
    assert is_echo("रुको जरा अभी चश्मा", agent)
    for scammer in ["मैडम आपके नाम पे एफआईआर है", "आप अभी पैसे भेजिए वरना गिरफ्तार होंगी", "मैं सीबीआई से बोल रहा हूं",
                    "अभी के अभी पैसे भेजो मैडम", "rathore.cbi@okaxis पे भेजिए"]:
        assert not is_echo(scammer, agent), scammer
