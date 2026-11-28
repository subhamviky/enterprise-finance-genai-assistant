"""Two customers from configuration (GCP-02 Phase C, item 7): the same code, a customer file per tenant, different
currency, limits, roles, number of approvers, expiry window and masking. The stand-ins play both tenants."""
import json

import pytest
from e2a_inmemory_adapters import InMemoryIdempotencyStore, InMemoryTransactionalStore

from genai_assistant_service.services.assistant import AssistantService, Forbidden
from genai_assistant_service.services.policy import Policy, PolicyBook
from genai_assistant_service.standins.landscape import Landscape, shared_transports
from genai_assistant_service.tools.catalog import tools


# ------------------------------------------------------------------------------------------------ the policy book
def test_each_customer_file_gives_its_tenant_its_own_policy():
    book = PolicyBook.load()
    acme, globex = book.for_tenant("acme"), book.for_tenant("globex")
    assert (acme.customer, acme.currencies, acme.approvals_required, acme.approver_role) == (
        "Acme Retail", ["EUR"], 1, "finance-approver")
    assert (globex.customer, globex.currencies, globex.approvals_required, globex.approver_role) == (
        "Globex Logistics", ["USD"], 2, "controller")
    assert str(acme.limits["WRITE_OFF"]) == "250.00" and str(globex.limits["WRITE_OFF"]) == "1000.00"
    assert acme.approval_ttl_seconds == 24 * 3600 and globex.approval_ttl_seconds == 48 * 3600


def test_an_unknown_tenant_gets_the_base_policy_and_what_a_file_does_not_name_stays_the_base():
    book = PolicyBook.load()
    other = book.for_tenant("initech")
    assert other.customer is None and other.approvals_required == 1
    globex = book.for_tenant("globex")
    assert globex.tools == book.base.tools and globex.max_inflight == book.base.max_inflight   # not overridden
    assert globex.entitlements["IntentAgent"] == ["analyst", "controller"]                     # overridden


def test_a_customer_masks_more_than_the_base_and_never_less():
    book = PolicyBook.load()
    text = "call +1 415-555-0134 about account 123456789012 or mail bo@globex.example"
    globex = book.for_tenant("globex").redact(text)
    assert "[PHONE]" in globex and "[ACCOUNT]" in globex and "[EMAIL]" in globex          # the base's e-mail mask is kept
    acme = book.for_tenant("acme").redact(text)
    assert "[PHONE]" not in acme and "[ACCOUNT]" not in acme and "[EMAIL]" in acme
    assert "5e0c3b8a-1f2d-4c6e-9a7b-000000000001" in book.for_tenant("globex").redact(
        "settlement 5e0c3b8a-1f2d-4c6e-9a7b-000000000001")                                # an id is not an account


def test_a_proposal_is_checked_against_its_customers_currency_and_limit():
    book = PolicyBook.load()
    usd = {"action": "WRITE_OFF", "settlement_id": "s", "amount": "600.00", "currency": "USD", "reason": "x"}
    settlement = {"amount": "5000.00", "currency": "USD", "status": "COMPLETED"}
    assert book.for_tenant("globex").check_proposal(usd, settlement) is None                 # within Globex's 1,000.00
    assert "policy limit" in book.for_tenant("acme").check_proposal(
        {**usd, "currency": "EUR"}, {**settlement, "currency": "EUR"})                       # over Acme's 250.00
    assert "not accepted for this customer" in book.for_tenant("globex").check_proposal(
        {**usd, "currency": "EUR"}, {**settlement, "currency": "EUR"})                       # Globex works in USD only


# ------------------------------------------------------------------------------------- two customers, one service
import httpx  # noqa: E402

from genai_assistant_service.services.assistant import Expired  # noqa: E402


@pytest.fixture
def two(monkeypatch):
    monkeypatch.delenv("E2A_PROVIDER_PROFILE", raising=False)
    monkeypatch.delenv("E2A_WORKLOAD_IDENTITY", raising=False)
    acme, globex = Landscape(tenant="acme", currency="EUR"), Landscape(tenant="globex", currency="USD")
    state = (InMemoryTransactionalStore(), InMemoryIdempotencyStore())
    clock = {"now": 1_800_000_000.0}

    def service():
        return AssistantService(tools=tools(transports=shared_transports(acme, globex)), state=state, clock=lambda: clock["now"])
    return type("Two", (), {"acme": acme, "globex": globex, "service": staticmethod(service), "clock": clock})


ANA_ACME, BO_ACME = ("ana@acme.example", "investigator"), ("bo@acme.example", "finance-approver")
ANA_GLOBEX, CARL, DEE = ("ana@globex.example", "analyst"), ("carl@globex.example", "controller"), ("dee@globex.example", "controller")


def test_the_same_request_is_decided_by_each_customers_own_rules(two):
    service = two.service()
    big = "Propose a write-off for bank line L-1003"                      # a difference of 300.00
    acme = service.ask(big, "acme", *ANA_ACME)
    globex = service.ask(big, "globex", *ANA_GLOBEX)
    assert acme["status"] != "AWAITING_APPROVAL" and "policy limit" in acme["answer"]           # Acme's limit is 250.00
    assert globex["status"] == "AWAITING_APPROVAL" and globex["proposal"]["amount"] == "300.00"   # Globex's is 1,000.00
    assert globex["proposal"]["currency"] == "USD" and "2 different controllers" in globex["answer"]


def test_each_customers_roles_are_its_own(two):
    service = two.service()
    with pytest.raises(Forbidden):                                          # an Acme role means nothing at Globex
        service.ask("Why is bank line L-1001 unmatched?", "globex", *("ana@acme.example", "investigator"))
    with pytest.raises(Forbidden):                                          # and the other way round
        service.ask("Why is bank line L-1001 unmatched?", "acme", *ANA_GLOBEX)
    assert service.ask("Why is bank line L-1001 unmatched?", "globex", *ANA_GLOBEX)["status"] == "COMPLETED"


def test_globex_needs_two_different_controllers_and_acme_one_approver(two):
    service = two.service()
    pending = service.ask("Propose a write-off for bank line L-1001", "globex", *ANA_GLOBEX)["approval_id"]
    with pytest.raises(Forbidden):                                          # the requester, and the wrong role
        service.approve(pending, "globex", *ANA_GLOBEX)
    first = service.approve(pending, "globex", *CARL)
    assert first["status"] == "AWAITING_APPROVAL" and first["approvers"] == ["carl@globex.example"]
    assert two.globex.posted() == []                                        # one controller is not enough
    again = service.approve(pending, "globex", *CARL)                       # the same one twice counts once
    assert again["approvers"] == ["carl@globex.example"] and two.globex.posted() == []
    done = service.approve(pending, "globex", *DEE)
    assert done["status"] == "COMPLETED" and len(two.globex.posted()) == 1
    assert done["receipt"]["approvers"] == ["carl@globex.example", "dee@globex.example"]
    assert two.globex.posted()[0]["amount"] == "12.50" and two.acme.posted() == []

    mine = service.ask("Propose a write-off for bank line L-1001", "acme", *ANA_ACME)["approval_id"]
    assert service.approve(mine, "acme", *BO_ACME)["status"] == "COMPLETED"      # Acme: one approver is the decision
    assert len(two.acme.posted()) == 1 and len(two.globex.posted()) == 1


def test_a_multi_step_approval_survives_a_restart_between_the_approvers(two):
    first = two.service()
    pending = first.ask("Propose a write-off for bank line L-1001", "globex", *ANA_GLOBEX)["approval_id"]
    first.approve(pending, "globex", *CARL)
    second = two.service()                                                  # a new revision: same state
    assert second.approvals.get("globex", pending)["approvers"] == ["carl@globex.example"]
    done = second.approve(pending, "globex", *DEE)
    assert done["status"] == "COMPLETED" and len(two.globex.posted()) == 1
    with pytest.raises(Forbidden):
        first.approve(pending, "globex", "eve@globex.example", "controller")      # decided: no third approval


def test_each_customer_has_its_own_window_to_decide(two):
    service = two.service()
    acme = service.ask("Propose a write-off for bank line L-1001", "acme", *ANA_ACME)["approval_id"]
    globex = service.ask("Propose a write-off for bank line L-1001", "globex", *ANA_GLOBEX)["approval_id"]
    two.clock["now"] += 30 * 3600                                           # 30 hours: past Acme's 24, inside Globex's 48
    with pytest.raises(Expired):
        service.approve(acme, "acme", *BO_ACME)
    assert service.approve(globex, "globex", *CARL)["status"] == "AWAITING_APPROVAL"
    two.clock["now"] += 20 * 3600                                           # 50 hours: Globex's window has closed too
    with pytest.raises(Expired):
        service.approve(globex, "globex", *DEE)
    assert two.acme.posted() == [] and two.globex.posted() == []


def test_one_customers_approval_cannot_be_decided_in_another_tenant(two):
    service = two.service()
    pending = service.ask("Propose a write-off for bank line L-1001", "globex", *ANA_GLOBEX)["approval_id"]
    from genai_assistant_service.services.assistant import NotFound
    with pytest.raises(NotFound):
        service.approve(pending, "acme", *BO_ACME)
    assert two.globex.posted() == [] and two.acme.posted() == []
