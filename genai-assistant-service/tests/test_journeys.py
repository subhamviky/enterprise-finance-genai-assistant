"""The four journeys of hub design note GCP-01 §6, against the stand-ins, on the simulated model."""
from decimal import Decimal

from conftest import ask
from genai_assistant_service.standins.landscape import ORDER, ORDER_FAILED, S_FLAGGED, S_SHORT

APPROVER = "bo@acme.example"


def test_investigate_an_unmatched_payment_read_only_and_cited(assistant, landscape):
    answer = ask(assistant, "Why is bank line L-1001 unmatched?")
    assert answer["status"] == "COMPLETED" and answer["intent"] == "INVESTIGATE"
    assert "recon:L-1001" in answer["citations"] and f"settlement:{S_SHORT}" in answer["citations"]
    assert "short by 12.50" in answer["answer"] and answer["inferred"]
    assert not [c for c in landscape.calls if c["method"] != "GET"]                  # read-only


def test_explain_a_flagged_settlement_separating_verified_from_inferred(assistant):
    answer = ask(assistant, f"Why was settlement {S_FLAGGED} flagged?")
    assert answer["intent"] == "EXPLAIN" and "FLAGGED" in answer["answer"]
    assert any(c.startswith("audit:") for c in answer["citations"])
    assert answer["verified"] and answer["inferred"]


def test_explain_an_order_through_its_settlement(assistant):
    answer = ask(assistant, f"Why was order {ORDER_FAILED} not paid?")
    assert f"order:{ORDER_FAILED}" in answer["citations"] and "declined by clearing" in answer["answer"]


def test_propose_then_a_second_person_approves_and_it_posts_once(assistant, landscape):
    proposed = ask(assistant, "Propose a write-off for bank line L-1001")
    assert proposed["status"] == "AWAITING_APPROVAL", proposed
    assert proposed["proposal"]["action"] == "WRITE_OFF" and proposed["proposal"]["amount"] == "12.50"
    assert landscape.posted() == []                                                   # nothing before approval
    approval = proposed["approval_id"]
    done = assistant.approve(approval, "acme", APPROVER, "finance-approver")
    assert done["status"] == "COMPLETED" and done["receipt"]["read_back"] is True
    posted = landscape.posted()
    assert len(posted) == 1 and Decimal(posted[0]["amount"]) == Decimal("12.50")
    assert assistant.approvals.get("acme", approval)["status"] == "APPROVED"
    assert assistant.approvals.receipt("acme", approval)["adjustment_id"] == posted[0]["adjustmentId"]


def test_order_status_investigation_cites_the_order(assistant):
    answer = ask(assistant, f"Explain order {ORDER}")
    assert f"order:{ORDER}" in answer["citations"]
