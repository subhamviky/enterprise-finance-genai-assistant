"""Approval recovery (GCP-02 Phase B, item 11): a proposal waits for a second person, days if need be. The wait must
survive an instance restart and a redeploy, the decision must post exactly once, and an approval nobody answers must
end in a defined state. A 'restart' here is a second AssistantService on the same state (what a new Cloud Run
revision is: new code, same Firestore)."""
import pytest
from e2a_inmemory_adapters import InMemoryIdempotencyStore, InMemoryTransactionalStore

from conftest import ask
from genai_assistant_service.services.assistant import Forbidden

APPROVER = ("bo@acme.example", "finance-approver")


@pytest.fixture
def shared_state():
    return InMemoryTransactionalStore(), InMemoryIdempotencyStore()


def test_an_approval_survives_a_restart_and_posts_once(make_assistant, landscape, shared_state):
    before = make_assistant(state=shared_state)
    approval = ask(before, "Propose a write-off for bank line L-1001")["approval_id"]
    assert landscape.posted() == []

    after = make_assistant(state=shared_state)                   # the redeploy: a new instance, the same state
    assert [a["approval_id"] for a in after.approvals.list("acme", "PENDING")] == [approval]
    done = after.approve(approval, "acme", *APPROVER)
    assert done["status"] == "COMPLETED" and done["receipt"]["read_back"] is True
    assert len(landscape.posted()) == 1

    with pytest.raises(Forbidden):                               # the old instance, deciding again: refused
        before.approve(approval, "acme", *APPROVER)
    with pytest.raises(Forbidden):
        after.approve(approval, "acme", *APPROVER)
    assert len(landscape.posted()) == 1                          # exactly once


def test_two_instances_deciding_at_the_same_time_post_once(make_assistant, landscape, shared_state):
    import threading
    a, b = make_assistant(state=shared_state), make_assistant(state=shared_state)
    approval = ask(a, "Propose a write-off for bank line L-1001")["approval_id"]
    results = []

    def decide(instance):
        try:
            results.append(instance.approve(approval, "acme", *APPROVER)["status"])
        except Forbidden:
            results.append("REFUSED")

    threads = [threading.Thread(target=decide, args=(i,)) for i in (a, b, a, b)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("COMPLETED") == 1 and len(landscape.posted()) == 1, results


def test_a_decision_taken_before_a_restart_is_still_final_after_it(make_assistant, landscape, shared_state):
    before = make_assistant(state=shared_state)
    approval = ask(before, "Propose a write-off for bank line L-1001")["approval_id"]
    before.reject(approval, "acme", *APPROVER)
    after = make_assistant(state=shared_state)
    assert after.approvals.get("acme", approval)["status"] == "REJECTED"
    with pytest.raises(Forbidden):
        after.approve(approval, "acme", *APPROVER)               # a rejection cannot be reversed by a restart
    assert landscape.posted() == []


# ---------------------------------------------------------------------------------------------- expiry
class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now

    def hours(self, n):
        self.now += n * 3600


def test_an_approval_nobody_answers_expires_and_posts_nothing(make_assistant, landscape, shared_state):
    from genai_assistant_service.services.assistant import Expired
    clock = Clock()
    assistant = make_assistant(state=shared_state, clock=clock)
    approval = ask(assistant, "Propose a write-off for bank line L-1001")["approval_id"]
    clock.hours(23)
    assert [a["approval_id"] for a in assistant.approvals.list("acme", "PENDING")] == [approval]   # still open

    clock.hours(2)                                               # 25 hours: past the 24-hour window
    assert assistant.approvals.list("acme", "PENDING") == []
    assert assistant.approvals.get("acme", approval)["status"] == "EXPIRED"
    with pytest.raises(Expired):
        assistant.approve(approval, "acme", *APPROVER)
    assert landscape.posted() == []                              # nothing was written

    restarted = make_assistant(state=shared_state, clock=clock)  # and a restart does not bring it back
    with pytest.raises(Expired):
        restarted.approve(approval, "acme", *APPROVER)
    assert landscape.posted() == []


def test_after_an_expiry_the_request_can_be_made_again_and_decided(make_assistant, landscape, shared_state):
    clock = Clock()
    assistant = make_assistant(state=shared_state, clock=clock)
    first = ask(assistant, "Propose a write-off for bank line L-1001")["approval_id"]
    clock.hours(30)
    again = ask(assistant, "Propose a write-off for bank line L-1001")
    assert again["status"] == "AWAITING_APPROVAL" and again["approval_id"] != first, again
    done = assistant.approve(again["approval_id"], "acme", *APPROVER)
    assert done["status"] == "COMPLETED" and len(landscape.posted()) == 1


def test_an_approval_decided_in_time_is_not_expired_later(make_assistant, landscape, shared_state):
    clock = Clock()
    assistant = make_assistant(state=shared_state, clock=clock)
    approval = ask(assistant, "Propose a write-off for bank line L-1001")["approval_id"]
    assistant.approve(approval, "acme", *APPROVER)
    clock.hours(48)
    assert assistant.approvals.get("acme", approval)["status"] == "APPROVED"      # a decision is final
