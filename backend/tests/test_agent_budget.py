"""DadiAgent keeps Groq's free tier (~8k tokens/min) alive: cheap regex every turn, the intel LLM only when useful."""

from voice_core.testing import FakeLLM
from voice_core.types import Turn

from dadi.agent import DadiAgent
from dadi.store import Store


def _agent(tmp_path, intel_replies):
    llm = FakeLLM(intel_replies)
    return DadiAgent(store=Store(tmp_path / "b.db"), llm=FakeLLM([]), intel_llm=llm, persona_key="dadi", seed=1), llm


async def test_intel_llm_runs_on_first_turn_every_second_turn_and_on_new_ids(tmp_path):
    agent, llm = _agent(tmp_path, ['{"scam_type":"digital_arrest","scam_confidence":0.7}'] * 10)
    h: list[Turn] = []

    async def say(text):
        h.append(Turn("scammer", text, float(len(h))))
        return await agent.on_user_turn(list(h))

    evt = await say("Main CBI se bol raha hoon madam")
    assert len(llm.calls) == 1 and evt["type"] == "intel" and evt["intel"]["scam_type"] == "digital_arrest"
    evt = await say("aapke naam pe FIR hai")  # nothing new, 1 turn since the LLM: regex only
    assert len(llm.calls) == 1 and evt["type"] == "intel"
    await say("aapko abhi arrest kar sakte hain")  # 2 turns since the LLM
    assert len(llm.calls) == 2
    evt = await say("paise rathore.cbi@okaxis pe bhejiye")  # regex found a new UPI ID: LLM right away
    assert len(llm.calls) == 3 and "rathore.cbi@okaxis" in evt["intel"]["upi_ids"]


async def test_regex_intel_is_saved_even_when_the_llm_is_skipped_or_fails(tmp_path):
    agent, llm = _agent(tmp_path, ["{}", "not json"])
    h = [Turn("scammer", "hello madam", 0.0)]
    await agent.on_user_turn(h)
    h.append(Turn("scammer", "call me on 9876543210", 1.0))
    evt = await agent.on_user_turn(h)
    assert "9876543210" in evt["intel"]["phones"]
    assert "9876543210" in agent.store.get_call(agent.call_id)["intel"]["phones"]
