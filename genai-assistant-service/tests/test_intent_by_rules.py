"""Reading the intent by rules first (GCP-02 Phase C, item 6): when the request says plainly what it wants, the model
is not asked; when it does not, it still is; and the switch turns it off."""
import pytest
from conftest import ask

from genai_assistant_service.agents.intent_agent import sure_intent
from genai_assistant_service.standins.landscape import ORDER, S_FLAGGED


@pytest.mark.parametrize("text,intent", [
    ("Why is bank line L-1001 unmatched?", "INVESTIGATE"),
    ("Propose a write-off for bank line L-1001", "PROPOSE"),
    ("refund bank line L-1002 please", "PROPOSE"),
    (f"Why was settlement {S_FLAGGED} flagged?", "EXPLAIN"),
    (f"Status of order {ORDER}?", "EXPLAIN"),
])
def test_a_plain_request_is_read_by_rules(text, intent):
    assert sure_intent(text)["intent"] == intent


@pytest.mark.parametrize("text", [
    "What is the weather today?",                      # no record named: the model decides it is unsupported
    "Tell me about L-1001",                            # a record but no plain intent: ask the model
    "hello",
])
def test_an_unclear_request_still_goes_to_the_model(text):
    assert sure_intent(text) is None


def test_the_switch_turns_it_off(monkeypatch):
    monkeypatch.setenv("GENAI_INTENT_BY_RULES", "false")
    assert sure_intent("Why is bank line L-1001 unmatched?") is None


def counting(assistant):
    """The assistant's own (simulated, rules-equipped) model, wrapped to record which agent called it."""
    calls, inner = [], assistant.llm.process_inference

    async def counted(messages=None, *args, **kwargs):
        calls.append(str((messages or [{}])[0].get("content", ""))[:30])
        return await inner(messages, *args, **kwargs)
    assistant.llm.process_inference = counted
    return calls


def test_intent_is_not_a_model_call_when_the_request_is_plain(assistant, landscape):
    calls = counting(assistant)
    answer = ask(assistant, "Why is bank line L-1001 unmatched?")
    assert answer["status"] == "COMPLETED" and "recon:L-1001" in answer["citations"], answer
    assert calls and not [c for c in calls if c.startswith("You are IntentAgent")], calls


def test_an_unclear_request_still_asks_the_model_for_the_intent(assistant, landscape):
    calls = counting(assistant)
    ask(assistant, "Tell me about L-1001")
    assert [c for c in calls if c.startswith("You are IntentAgent")], calls


def test_the_ids_are_still_the_ones_in_the_request_and_a_proposal_still_waits(assistant, landscape):
    answer = ask(assistant, "Propose a write-off for bank line L-1001")
    assert answer["status"] == "AWAITING_APPROVAL" and answer["proposal"]["settlement_id"], answer
    assert landscape.posted() == []
