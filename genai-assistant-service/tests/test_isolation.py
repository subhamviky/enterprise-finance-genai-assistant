"""Tenant isolation and fair capacity (GCP-02 Phase C, item 14): many customers through one service. Nothing one tenant
does may be seen by, change, or starve another. Simulated model, stand-ins for the four systems: no quota, no cloud."""
import threading

import pytest
from e2a_inmemory_adapters import InMemoryIdempotencyStore, InMemoryTransactionalStore

from genai_assistant_service.services.assistant import AssistantService, Forbidden, NotFound
from genai_assistant_service.standins.landscape import Landscape, shared_transports
from genai_assistant_service.tools.catalog import tools

TENANTS = [f"t{n:02d}" for n in range(24)]            # no customer file: the base policy
INV, APP = ("ana@x.example", "investigator"), ("bo@x.example", "finance-approver")


@pytest.fixture
def many(monkeypatch):
    monkeypatch.delenv("E2A_PROVIDER_PROFILE", raising=False)
    monkeypatch.delenv("E2A_WORKLOAD_IDENTITY", raising=False)
    landscapes = {t: Landscape(tenant=t) for t in TENANTS}
    state = (InMemoryTransactionalStore(), InMemoryIdempotencyStore())
    service = AssistantService(tools=tools(transports=shared_transports(*landscapes.values())), state=state)
    return service, landscapes


def test_many_tenants_asking_the_same_thing_each_get_their_own_proposal_and_posting(many):
    service, landscapes = many
    approvals = {t: service.ask("Propose a write-off for bank line L-1001", t, *INV)["approval_id"] for t in TENANTS}
    assert len(set(approvals.values())) == len(TENANTS)                           # no two tenants share an approval
    for t in TENANTS:
        assert [a["approval_id"] for a in service.approvals.list(t)] == [approvals[t]]     # a tenant lists only its own
    for t in TENANTS:
        assert service.approve(approvals[t], t, *APP)["status"] == "COMPLETED"
    for t, landscape in landscapes.items():
        assert len(landscape.posted()) == 1                                       # one posting each, in its own ledger
        assert {c["tenant"] for c in landscape.calls} == {t}                      # and every call it saw named its tenant


def test_a_tenant_cannot_see_or_decide_anothers_approval(many):
    service, landscapes = many
    mine = service.ask("Propose a write-off for bank line L-1001", "t00", *INV)["approval_id"]
    assert service.approvals.get("t01", mine) is None
    for other in ("t01", "t23", "unknown-tenant"):
        with pytest.raises(NotFound):
            service.approve(mine, other, *APP)
        with pytest.raises(NotFound):
            service.reject(mine, other, *APP)
    assert all(lnd.posted() == [] for lnd in landscapes.values())
    assert service.approve(mine, "t00", *APP)["status"] == "COMPLETED"            # and it is still decidable by its owner


def test_the_same_client_idempotency_key_in_two_tenants_is_two_requests(many):
    """A key a client chooses ('retry-7') must not make one tenant receive another's result or conflict with it."""
    service, landscapes = many
    a = service.ask("Propose a write-off for bank line L-1001", "t00", *INV, idempotency_key="retry-7")
    b = service.ask("Propose a write-off for bank line L-1001", "t01", *INV, idempotency_key="retry-7")
    assert a["status"] == b["status"] == "AWAITING_APPROVAL" and a["approval_id"] != b["approval_id"]
    assert service.approve(b["approval_id"], "t01", *APP)["status"] == "COMPLETED"
    assert len(landscapes["t01"].posted()) == 1 and landscapes["t00"].posted() == []
    assert service.approve(a["approval_id"], "t00", *APP)["status"] == "COMPLETED"
    assert len(landscapes["t00"].posted()) == 1


def test_a_tenant_never_receives_another_tenants_records(many):
    service, landscapes = many
    answer = service.ask("Why is bank line L-1001 unmatched?", "t07", *INV)
    assert answer["status"] == "COMPLETED"
    assert all(c["tenant"] == "t07" for c in landscapes["t07"].calls)
    assert all(lnd.calls == [] for t, lnd in landscapes.items() if t != "t07")    # no other tenant's system was touched


# ----------------------------------------------------------------------------------------------- a noisy tenant
class Gate:
    """A tenant whose reconciliation answers only when the gate opens: its requests stay in flight. The wait is
    asynchronous (like a slow network call), so it holds the request without freezing the event loop."""

    def __init__(self):
        self.open, self.entered = threading.Event(), threading.Semaphore(0)


def gated_transports(noisy: Landscape, quiet: Landscape, gate: Gate):
    import asyncio
    import httpx

    async def handler(request, system):
        tenant = request.headers.get("X-Tenant-Id")
        if tenant == noisy.tenant and system == "recon" and request.url.path == "/service/v1/exceptions":
            gate.entered.release()
            while not gate.open.is_set():
                await asyncio.sleep(0.01)
        return (noisy if tenant == noisy.tenant else quiet).respond(system, request)

    return {key: httpx.MockTransport(lambda r, system=system: handler(r, system))
            for key, system in (("RECONCILIATION_API_URL", "recon"), ("SETTLEMENT_API_URL", "settlement"),
                                ("O2C_API_URL", "o2c"), ("AUDIT_API_URL", "audit"))}


def test_a_noisy_tenant_does_not_starve_a_quiet_one(monkeypatch):
    from e2a import NFRViolationError
    monkeypatch.delenv("E2A_PROVIDER_PROFILE", raising=False)
    monkeypatch.delenv("E2A_WORKLOAD_IDENTITY", raising=False)
    noisy, quiet, gate = Landscape(tenant="noisy"), Landscape(tenant="quiet"), Gate()
    service = AssistantService(tools=tools(transports=gated_transports(noisy, quiet, gate)))
    cap = service.policy.max_inflight_per_tenant
    results, lock = [], threading.Lock()

    def flood():
        try:
            outcome = service.ask("Why is bank line L-1001 unmatched?", "noisy", *INV)["status"]
        except NFRViolationError as refused:
            outcome = "REFUSED"
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=flood) for _ in range(service.policy.max_inflight + 8)]
    [t.start() for t in threads]
    for _ in range(cap):
        assert gate.entered.acquire(timeout=10), "the noisy tenant's admitted requests are in flight"
    # the noisy tenant now holds its share; the quiet tenant is served at once
    assert service.ask("Why is bank line L-1001 unmatched?", "quiet", *INV)["status"] == "COMPLETED"
    gate.open.set()
    [t.join(20) for t in threads]
    assert results.count("COMPLETED") == cap and results.count("REFUSED") == len(threads) - cap, results
