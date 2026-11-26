"""The failure-injection matrix of hub design note GCP-01 §6, one test per row, against the stand-ins.
(Concurrent bank-line matches are reconciliation-service's own test; cold start and partial deploy
are runbook rows.)"""
import json
import threading

import pytest
from e2a_simulated_llm import SimulatedLLMService, system_contains

from conftest import ask
from genai_assistant_service.services.assistant import Forbidden, NotFound
from genai_assistant_service.standins.landscape import S_SHORT

APPROVER = ("bo@acme.example", "finance-approver")


class DownLLM(SimulatedLLMService):
    """The model is unavailable: every call fails (a Gemini 429 or a timeout)."""

    async def process_inference(self, *args, **kwargs):
        return {"status": "FAILED", "error": "429 RESOURCE_EXHAUSTED", "error_type": "QuotaExceeded"}


def proposed(assistant):
    answer = ask(assistant, "Propose a write-off for bank line L-1001")
    assert answer["status"] == "AWAITING_APPROVAL", answer
    return answer["approval_id"]


def test_model_down_investigation_degrades_to_the_verified_facts(make_assistant, landscape):
    assistant = make_assistant(llm=DownLLM())
    answer = ask(assistant, "Why is bank line L-1001 unmatched?")
    assert answer["status"] == "COMPLETED" and answer["degraded"] is True
    assert "recon:L-1001" in answer["citations"] and answer["inferred"] == []      # facts only, no reasoning


def test_model_down_never_proposes_and_never_posts(make_assistant, landscape):
    assistant = make_assistant(llm=DownLLM())
    answer = ask(assistant, "Propose a write-off for bank line L-1001")
    assert answer["status"] == "COMPLETED" and answer["proposal"]["action"] == "NONE" and answer["degraded"]
    assert landscape.posted() == []


def test_an_answer_with_invented_citations_is_refused(make_assistant, landscape):
    from genai_assistant_service.services.simulated import _intent
    llm = (SimulatedLLMService().add_rule("intent", system_contains("You are IntentAgent."), _intent)
           .add_rule("liar", system_contains("You are InvestigatorAgent"),
                     '{"answer": "Settlement 11111111-2222-3333-4444-555555555555 failed.", '
                     '"citations": ["settlement:11111111-2222-3333-4444-555555555555"], "verified": [], "inferred": []}'))
    answer = ask(make_assistant(llm=llm), "Why is bank line L-1001 unmatched?")
    assert "11111111-2222" not in answer["answer"] and answer["degraded"] is True


def test_unknown_settlement_answer_is_unknown_and_the_retry_posts_once(assistant, landscape):
    approval = proposed(assistant)
    landscape.faults["settlement:/api/v1/settlements/" + S_SHORT + "/adjustments"] = "timeout"
    first = assistant.approve(approval, "acme", *APPROVER)
    assert first["status"] != "COMPLETED" and landscape.posted() == []
    with pytest.raises(Forbidden):                     # decided once: a second approval does not run it again
        assistant.approve(approval, "acme", *APPROVER)
    landscape.faults.clear()
    again = ask(assistant, "Propose a write-off for bank line L-1001")          # same proposal, same key
    assert again["status"] in ("AWAITING_APPROVAL", "RECOVERY_REQUIRED", "IN_PROGRESS", "CONFLICT", "REPLAYED"), again
    assert len(landscape.posted()) <= 1


def test_a_replayed_approval_posts_nothing_twice(assistant, landscape):
    approval = proposed(assistant)
    assistant.approve(approval, "acme", *APPROVER)
    with pytest.raises(Forbidden):
        assistant.approve(approval, "acme", *APPROVER)
    assert len(landscape.posted()) == 1


def test_concurrent_approvals_post_once(assistant, landscape):
    approval = proposed(assistant)
    results, barrier = [], threading.Barrier(4)

    def approve():
        barrier.wait()
        try:
            results.append(assistant.approve(approval, "acme", *APPROVER)["status"])
        except Forbidden as e:
            results.append(f"refused: {e}")
    threads = [threading.Thread(target=approve) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("COMPLETED") == 1 and len(landscape.posted()) == 1, results


def test_the_requester_cannot_approve_their_own_adjustment(assistant, landscape):
    approval = proposed(assistant)
    with pytest.raises(Forbidden, match="four eyes"):
        assistant.approve(approval, "acme", "ana@acme.example", "finance-approver")
    assert landscape.posted() == []


def test_only_an_approver_may_decide(assistant, landscape):
    approval = proposed(assistant)
    with pytest.raises(Forbidden, match="finance-approver"):
        assistant.approve(approval, "acme", "cy@acme.example", "investigator")
    assert landscape.posted() == []


def test_another_tenant_cannot_see_or_decide_an_approval(assistant, landscape):
    approval = proposed(assistant)
    with pytest.raises(NotFound):
        assistant.approve(approval, "globex", *APPROVER)
    assert assistant.approvals.list("globex") == [] and landscape.posted() == []


def test_a_cross_tenant_request_reads_nothing(assistant, landscape):
    answer = assistant.ask("Why is bank line L-1001 unmatched?", "globex", "eve@globex.example", "investigator")
    assert answer["status"] == "NOT_FOUND" and all(c["tenant"] == "globex" for c in landscape.calls)


def test_a_rejected_proposal_posts_nothing(assistant, landscape):
    approval = proposed(assistant)
    assert assistant.reject(approval, "acme", *APPROVER)["status"] == "REJECTED"
    assert landscape.posted() == [] and assistant.approvals.get("acme", approval)["status"] == "REJECTED"


def test_settlement_refuses_above_its_own_limit_and_the_receipt_says_so(make_assistant, landscape):
    from decimal import Decimal
    from genai_assistant_service.services.policy import Policy
    policy = Policy()
    policy.limits["WRITE_OFF"] = Decimal("1000.00")       # a laxer policy here: settlement-service still refuses
    landscape.data["exceptions"][2]["proposal"] = None
    assistant = make_assistant(policy=policy)
    answer = ask(assistant, "Propose a write-off for bank line L-1003")
    assert answer["status"] == "AWAITING_APPROVAL" and answer["proposal"]["amount"] == "300.00"
    landscape.WRITE_OFF_LIMIT = Decimal("100.00")
    done = assistant.approve(answer["approval_id"], "acme", *APPROVER)
    assert done["status"] == "FAILED" and done["receipt"]["outcome"] == "NOT_COMMITTED" and landscape.posted() == []


def test_a_settlement_that_changed_since_the_proposal_is_not_adjusted(assistant, landscape):
    approval = proposed(assistant)
    landscape.data["settlements"][S_SHORT]["status"] = "REVERSED"
    done = assistant.approve(approval, "acme", *APPROVER)
    assert done["status"] == "FAILED" and landscape.posted() == []


class FencedLLM(SimulatedLLMService):
    """Gemini's habit: JSON inside a code fence."""

    async def process_inference(self, *args, **kwargs):
        return {"status": "SUCCESS", "text": '```json\n{"intent": "INVESTIGATE", "line_id": "L-1001"}\n```', "tokens_used": 10}


class ProseLLM(SimulatedLLMService):
    """The model answers in words, not JSON."""

    async def process_inference(self, *args, **kwargs):
        return {"status": "SUCCESS", "text": "Sure, this looks like an unmatched bank line.", "tokens_used": 10}


def test_a_fenced_model_reply_is_read(make_assistant, landscape):
    answer = ask(make_assistant(llm=FencedLLM()), "Why is bank line L-1001 unmatched?")
    assert answer["status"] == "COMPLETED" and "recon:L-1001" in answer["citations"], answer


def test_an_unreadable_model_reply_falls_back_to_rules_and_still_investigates(make_assistant, landscape):
    answer = ask(make_assistant(llm=ProseLLM()), "Why is bank line L-1001 unmatched?")
    assert answer["status"] == "COMPLETED" and "recon:L-1001" in answer["citations"], answer


def test_a_fenced_reply_in_every_agent_is_read(make_assistant, landscape):
    """Intent, investigation and proposal all read JSON inside a code fence."""
    import json as _json

    class AllFenced(SimulatedLLMService):
        async def process_inference(self, messages=None, *args, **kwargs):
            system = str((messages or [{}])[0].get("content", ""))
            if system.startswith("You are IntentAgent"):
                body = {"intent": "PROPOSE", "line_id": "L-1001"}
            else:
                return await super().process_inference(messages, *args, **kwargs)
            return {"status": "SUCCESS", "text": "```json\n" + _json.dumps(body) + "\n```", "tokens_used": 10}

    answer = ask(make_assistant(llm=AllFenced()), "Propose a write-off for bank line L-1001")
    assert answer["status"] in ("AWAITING_APPROVAL", "COMPLETED"), answer


def test_the_same_adjustment_worded_differently_is_the_same_claim():
    """A live model words its reason differently on each call; the claim must not depend on the wording."""
    from genai_assistant_service.workflow.investigation_workflow import InvestigationWorkflow
    workflow = InvestigationWorkflow()
    base = {"tenant_id": "acme", "user_id": "ana", "line_id": "L-1",
            "proposal": {"action": "WRITE_OFF", "settlement_id": "s-1", "amount": "2.50", "currency": "EUR"}}
    reworded = {**base, "proposal": {**base["proposal"], "reason": "likely a bank fee"}}
    other_reason = {**base, "proposal": {**base["proposal"], "reason": "short payment"}}
    assert workflow._generate_idempotency_key(reworded, None) == workflow._generate_idempotency_key(other_reason, None)
    assert workflow._request_fingerprint(reworded, None) == workflow._request_fingerprint(other_reason, None)
    bigger = {**base, "proposal": {**base["proposal"], "amount": "3.00"}}
    assert workflow._generate_idempotency_key(bigger, None) != workflow._generate_idempotency_key(base, None)


def test_an_identifier_the_model_returns_with_sentence_punctuation_is_still_looked_up(make_assistant, landscape):
    """Live: 'Status of order ORD-...?' made the model return the id with its question mark, and the tool refused it."""
    import json
    from genai_assistant_service.standins.landscape import ORDER as ORDER_PAID

    class PunctuatedLLM(SimulatedLLMService):
        async def process_inference(self, *args, **kwargs):
            return {"status": "SUCCESS", "text": json.dumps({"intent": "EXPLAIN", "order_id": ORDER_PAID + "?"}),
                    "tokens_used": 5}

    answer = ask(make_assistant(llm=PunctuatedLLM()), f"Status of order {ORDER_PAID}?")
    assert answer["status"] == "COMPLETED" and f"order:{ORDER_PAID}" in answer["records_read"], answer


def _reply(by_agent):
    """A model that answers each agent as a live one did in the first cloud evaluation (GCP-01)."""
    class Live(SimulatedLLMService):
        async def process_inference(self, messages=None, *args, **kwargs):
            system = str((messages or [{}])[0].get("content", ""))
            for prefix, body in by_agent.items():
                if system.startswith(prefix):
                    return {"status": "SUCCESS", "text": json.dumps(body), "tokens_used": 5}
            return await super().process_inference(messages, *args, **kwargs)
    return Live()


def test_a_draft_with_a_numeric_amount_is_read_and_still_checked_by_the_policy(make_assistant, landscape):
    from genai_assistant_service.standins.landscape import S_SHORT
    llm = _reply({"You are IntentAgent": {"intent": "PROPOSE", "line_id": "L-1001"},
                  "You are ProposalAgent": {"action": "WRITE_OFF", "settlement_id": S_SHORT, "amount": 12.5,
                                            "currency": "EUR", "reason": "short payment"}})
    answer = ask(make_assistant(llm=llm), "Propose a write-off for bank line L-1001")
    assert answer["status"] == "AWAITING_APPROVAL" and answer["proposal"]["amount"] == "12.50", answer
    too_big = _reply({"You are IntentAgent": {"intent": "PROPOSE", "line_id": "L-1001"},
                      "You are ProposalAgent": {"action": "WRITE_OFF", "settlement_id": S_SHORT, "amount": 900,
                                                "currency": "EUR", "reason": "x"}})
    refused = ask(make_assistant(llm=too_big), "Propose a write-off for bank line L-1001")
    assert refused["status"] != "AWAITING_APPROVAL" and "policy limit" in refused["answer"], refused


def test_a_draft_of_none_with_null_fields_is_a_proposal_of_nothing_not_a_failure(make_assistant, landscape):
    llm = _reply({"You are IntentAgent": {"intent": "PROPOSE", "line_id": "L-1002"},
                  "You are ProposalAgent": {"action": "NONE", "settlement_id": None, "amount": None,
                                            "currency": None, "reason": "nothing to adjust"}})
    answer = ask(make_assistant(llm=llm), "Propose a write-off for bank line L-1002")
    assert answer["status"] == "COMPLETED" and "nothing to adjust" in answer["answer"], answer
    assert "not valid JSON" not in answer["answer"] and landscape.posted() == []


def test_the_rules_arbitrate_when_the_model_calls_a_request_that_names_a_record_unsupported(make_assistant, landscape):
    from genai_assistant_service.standins.landscape import ORDER
    llm = _reply({"You are IntentAgent": {"intent": "UNSUPPORTED", "line_id": None, "settlement_id": None,
                                          "order_id": None}})
    answer = ask(make_assistant(llm=llm), f"Status of order {ORDER}?")
    assert answer["status"] == "COMPLETED" and f"order:{ORDER}" in answer["records_read"], answer
    nothing = ask(make_assistant(llm=llm), "What is the weather today?")
    assert nothing["status"] == "COMPLETED" and "I investigate" in nothing["answer"], nothing    # still unsupported


def _exception(landscape, line="L-1001"):
    return next(c for c in landscape.data["exceptions"] if c["line_id"] == line)


def test_an_approved_write_off_closes_the_reconciliation_exception(assistant, landscape):
    approval = proposed(assistant)
    done = assistant.approve(approval, "acme", *APPROVER)
    posted = landscape.posted()
    assert len(posted) == 1 and "L-1001" in posted[0]["reference"]          # the ledger row names the line
    assert _exception(landscape)["status"] == "RESOLVED"
    assert done["receipt"]["exception"]["closed"] is True
    assert "L-1001 is RESOLVED" in done["answer"]


def test_a_reconciliation_outage_leaves_the_exception_open_but_keeps_the_posting(assistant, landscape):
    approval = proposed(assistant)
    landscape.faults["recon:/service/v1/exceptions/L-1001/resolve"] = 503
    done = assistant.approve(approval, "acme", *APPROVER)
    assert len(landscape.posted()) == 1 and done["status"] == "COMPLETED"    # the posting stands
    assert _exception(landscape)["status"] == "OPEN"
    assert done["receipt"]["exception"]["closed"] is False
    assert "stays open" in done["answer"]


def test_a_write_off_on_the_wrong_candidate_or_amount_is_refused(assistant, landscape):
    """A live model once chose another COMPLETED settlement than the one the bank line is short against."""
    from genai_assistant_service.services.policy import Policy
    line = {"line_id": "L-1", "amount": "987.50"}
    case = {"candidates": [{"settlement_id": "S-A"}, {"settlement_id": "S-B"}]}
    short = {"amount": "1000.00"}
    check = Policy.check_against_bank_line
    ok = {"action": "WRITE_OFF", "settlement_id": "S-A", "amount": "12.50"}
    assert check(ok, short, line, case) is None
    assert "not a candidate" in check({**ok, "settlement_id": "S-Z"}, short, line, case)
    assert "does not match" in check(ok, {"amount": "998.00"}, line, case)       # this settlement is short by 10.50
    assert "does not match" in check({**ok, "amount": "10.00"}, short, line, case)
    assert check({**ok, "action": "REFUND"}, short, line, case)                    # a short payment is not refunded
    assert check(ok, short, None, None) is None                                    # a question about a settlement only


def test_two_equally_fitting_settlements_are_not_guessed_and_a_named_one_is_honoured():
    from genai_assistant_service.services.policy import Policy
    line = {"line_id": "L-1", "amount": "1365.50"}
    case = {"candidates": [{"settlement_id": "S-A"}, {"settlement_id": "S-B"}]}
    both = {"S-A": {"amount": "1368.00", "status": "COMPLETED"}, "S-B": {"amount": "1368.00", "status": "COMPLETED"}}
    proposal = {"action": "WRITE_OFF", "settlement_id": "S-B", "amount": "2.50"}
    check = Policy.check_against_bank_line
    assert "name the settlement" in check(proposal, both["S-B"], line, case, settlements=both)
    assert check(proposal, both["S-B"], line, case, named="S-B", settlements=both) is None
    assert "names settlement S-A" in check(proposal, both["S-B"], line, case, named="S-A", settlements=both)
    only_one = {"S-A": both["S-A"], "S-B": {"amount": "1400.00", "status": "COMPLETED"}}
    assert check({**proposal, "settlement_id": "S-A"}, both["S-A"], line, case, settlements=only_one) is None
