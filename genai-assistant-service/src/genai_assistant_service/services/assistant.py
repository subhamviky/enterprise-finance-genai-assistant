"""The assistant: composition root and its capabilities.

ask()      validate the request, then InvestigationWorkflow.execute(): route -> gather evidence ->
           investigate, explain or propose -> (an actionable proposal) pause for approval.
approve()  a second person with the approver role approves: resume() continues at the execution
           step, under the same idempotency key, exactly once; the receipt is kept.
reject()   the same person refuses: nothing is posted.

The model is bound from E2A_PROVIDER_PROFILE (services/bindings.py): "simulated" by default (its
behaviour in services/simulated.py), "gemini_api" on the free tier. Calls to the systems of record
carry this service's own identity when E2A_WORKLOAD_IDENTITY is set (e2a_adapters.workload)."""
import contextlib
import os
import threading
from typing import Any, Dict, Optional

from e2a import CapacityRefusal, ResumeRefused, resolve_config

from ..tools.catalog import tools as default_tools
from ..workflow.investigation_workflow import InvestigationWorkflow
from .bindings import DEFAULT_PROFILE
from .governance import ServiceGovernance, governing
from .policy import Policy
from .state import state_ports
from .policy import PolicyBook
from .stores import ApprovalStore
from .validation import ServiceValidation

HELP = ("I investigate unmatched bank lines, explain delayed or flagged settlements and propose write-offs or "
        "refunds for a second person to approve. Name the bank line, settlement or order (ORD-...).")


class Forbidden(Exception):
    """The caller may not do this (HTTP 403)."""


class NotFound(Exception):
    """No such approval for this tenant (HTTP 404)."""


class Expired(Exception):
    """The approval was not decided in time and nothing was posted; ask again (HTTP 410)."""


class AssistantService:
    def __init__(self, tools: Optional[Dict[str, Any]] = None, llm=None, state=None, policy: Policy = None,
                 config: Optional[Dict] = None, clock=None) -> None:
        import time
        from e2a import bindings_from_profile
        from e2a_adapters.workload import workload_credentials
        self.book = PolicyBook.of(policy) if policy is not None else PolicyBook.load()
        self.policy = self.book.base
        self.governance = ServiceGovernance(self.book)
        self.validation = ServiceValidation(self.book)
        rows, claims = state or state_ports()
        self.approvals = ApprovalStore(rows, lambda tenant: self.book.for_tenant(tenant).approval_ttl_seconds,
                                       clock or time.time)
        bindings = bindings_from_profile(resolve_config("provider_profile", {}) or DEFAULT_PROFILE, verify=True)
        self.llm = llm or bindings.llm_service
        if llm is None and bindings.profile.name == "simulated":
            from .simulated import add_rules
            add_rules(self.llm)
        credentials = workload_credentials()
        self.config = {**bindings.config(tools=tools or default_tools()), "llm_service": self.llm,
                       "governance_engine": self.governance, "validation_service": self.validation,
                       "idempotency_store": claims, "checkpoint_store": self.approvals,
                       "max_token_budget": self.policy.max_token_budget, "timeout": 8.0, "retries": 2,
                       **({"credential_provider": credentials} if credentials is not None else {}),
                       **(config or {})}
        self.workflow = InvestigationWorkflow(policy=self.book)
        self._tenant_inflight: Dict[str, int] = {}
        self._tenant_lock = threading.Lock()

    # --------------------------------------------------------------------- capabilities
    def ask(self, text: str, tenant_id: str, user_id: str, role: str,
            idempotency_key: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        return self.ask_traced(text, tenant_id, user_id, role, idempotency_key, correlation_id)[0]

    def ask_traced(self, text, tenant_id, user_id, role, idempotency_key=None, correlation_id=None):
        """ask(), and the final state (steps, tools called, evaluation) the release gate scores."""
        state = {"tenant_id": tenant_id, "user_id": user_id, "role": role, "query": text}
        if correlation_id:                       # the caller's id follows the request through every tool call
            state["correlation_id"] = correlation_id
        result = self.validation.validate("IntentAgent", state, self.config)
        if not result["valid"]:
            if result.get("forbidden"):
                raise Forbidden("; ".join(result["errors"]))
            raise ValueError("; ".join(result["errors"]))
        with self._admit(tenant_id), self.governance.limiter.slot(), governing(tenant_id):
            state = self.workflow.execute(state, self.config, idempotency_key=idempotency_key)
        return self._outcome(state), state

    def approve(self, approval_id: str, tenant_id: str, user_id: str, role: str) -> Dict[str, Any]:
        policy = self.book.for_tenant(tenant_id)
        approvers = [user_id]
        if policy.approvals_required > 1:                    # this customer wants several different approvers
            waiting = self._record_approver(policy, approval_id, tenant_id, user_id, role)
            if waiting is not None:
                return waiting
            approvers = list(self.approvals.get(tenant_id, approval_id).get("approvers") or [user_id])
        state = self._decide(approval_id, tenant_id, {"approved": True, "decided_by": user_id, "role": role})
        receipt = state.get("receipt")
        if receipt:
            receipt["approvers"] = approvers
            self.approvals.record_receipt(tenant_id, approval_id, receipt)
        return self._outcome(state)

    @contextlib.contextmanager
    def _admit(self, tenant_id):
        """Fair capacity: one tenant may have only max_inflight_per_tenant requests in flight in this instance, so a
        noisy customer is refused (retryable, HTTP 503) before it can fill the slots a quiet one needs."""
        cap = self.policy.max_inflight_per_tenant
        with self._tenant_lock:
            n = self._tenant_inflight.get(tenant_id, 0)
            if n >= cap:
                raise CapacityRefusal(f"tenant capacity exceeded ({cap} requests in flight); retry later",
                                      "tenant-capacity")
            self._tenant_inflight[tenant_id] = n + 1
        try:
            yield
        finally:
            with self._tenant_lock:
                self._tenant_inflight[tenant_id] -= 1
                if not self._tenant_inflight[tenant_id]:
                    del self._tenant_inflight[tenant_id]

    def _approvers_text(self, tenant_id) -> str:
        policy = self.book.for_tenant(tenant_id)
        n = policy.approvals_required
        return f"{n} different {policy.approver_role}s" if n > 1 else f"a {policy.approver_role}"

    def _record_approver(self, policy, approval_id, tenant_id, user_id, role) -> Optional[Dict[str, Any]]:
        """One approver of several. The same checks as a single decision (the role, and not the requester), then the
        approver is recorded; the workflow is resumed, and the adjustment posted, only by the last one needed."""
        current = self.approvals.get(tenant_id, approval_id)
        if current is None:
            raise NotFound(f"approval {approval_id}")
        if current["status"] == "EXPIRED":
            raise Expired(f"approval {approval_id} expired: it was not decided in time, nothing was posted; "
                          "make the request again")
        if role != policy.approver_role:
            raise Forbidden(f"only role '{policy.approver_role}' may decide")
        if policy.four_eyes and user_id == current["requested_by"]:
            raise Forbidden("four eyes: the requester cannot approve their own adjustment")
        approvers = self.approvals.add_approver(tenant_id, approval_id, user_id)
        if approvers is None:
            raise Forbidden(f"approval {approval_id} was already decided")
        if len(approvers) < policy.approvals_required:
            missing = policy.approvals_required - len(approvers)
            return {"status": "AWAITING_APPROVAL", "approval_id": approval_id, "approvers": approvers,
                    "answer": f"Approved by {', '.join(approvers)}; nothing is posted until {missing} more different "
                              f"{policy.approver_role}{'s' if missing > 1 else ''} approve."}
        return None

    def reject(self, approval_id: str, tenant_id: str, user_id: str, role: str) -> Dict[str, Any]:
        self._decide(approval_id, tenant_id, {"approved": False, "decided_by": user_id, "role": role})
        return {"status": "REJECTED", "approval_id": approval_id,
                "answer": f"Approval {approval_id} rejected: nothing was posted to the ledger."}

    # -------------------------------------------------------------------------- helpers
    def _decide(self, approval_id, tenant_id, decision) -> Dict:
        try:
            with self._admit(tenant_id), self.governance.limiter.slot(), governing(tenant_id):
                return self.workflow.resume(approval_id, decision, self.config, tenant_id=tenant_id)
        except ResumeRefused as refused:
            if refused.code == "UNKNOWN_CHECKPOINT":
                raise NotFound(f"approval {approval_id}") from refused
            current = self.approvals.get(tenant_id, approval_id)
            if current is not None and current["status"] == "EXPIRED":
                raise Expired(f"approval {approval_id} expired: it was not decided in time, nothing was posted; "
                              "make the request again") from refused
            raise Forbidden(refused.reason) from refused

    def _answer(self, state, status, text, **fields) -> Dict[str, Any]:
        redacted = self.governance.redact_response(state, {"text": text}, self.config)["text"]
        return {"status": status, "intent": state.get("intent"), "answer": redacted,
                "correlation_id": state.get("correlation_id"), **fields}

    @staticmethod
    def _closure(receipt) -> str:
        e = receipt.get("exception")
        if not e:
            return ""
        return (f" Exception {e['line_id']} is {e.get('status') or 'closed'}." if e["closed"] else
                f" Exception {e['line_id']} was not closed ({e.get('detail') or 'reconciliation did not confirm'}); it stays open.")

    def _outcome(self, state) -> Dict[str, Any]:
        refusal = state.get("refusal")
        if refusal:                                       # a typed governance refusal
            if refusal["code"] == "ENTITLEMENT":
                raise Forbidden(refusal["reason"])
            if refusal["code"] == "CAPACITY":
                raise CapacityRefusal(refusal["reason"], refusal["stage"])
            if refusal["code"] == "FIREWALL":
                return self._answer(state, "REFUSED", refusal["reason"])
            return self._answer(state, "FAILED", f"The request was not executed ({refusal['reason']}).")
        intent = state.get("intent", "UNSUPPORTED")
        if intent == "UNSUPPORTED":
            return self._answer(state, "COMPLETED", HELP)
        if not state.get("evidence"):
            gaps = state.get("evidence_gaps") or ["no record was found"]
            return self._answer(state, "NOT_FOUND", "No record answers this request: " + "; ".join(gaps) + ".",
                                degraded=True)
        status = state.get("status")
        if status == "AWAITING_WEBHOOK":
            p = state["proposal"]
            return self._answer(state, "AWAITING_APPROVAL",
                                f"Proposed {p['action']} of {p['amount']} {p['currency']} on settlement "
                                f"{p['settlement_id']}: {p['reason']}. It waits for {self._approvers_text(state.get('tenant_id'))} "
                                f"other than you (approval {state['checkpoint_id']}); nothing has been posted.",
                                approval_id=state["checkpoint_id"], proposal=p,
                                citations=[e["id"] for e in state["evidence"]])
        if state.get("receipt"):
            r = state["receipt"]
            text = (f"Adjustment {r.get('adjustment_id')} posted to the ledger (read back: {r.get('read_back')})."
                    + self._closure(r) if r["outcome"] == "COMMITTED" else
                    f"The adjustment was not posted ({r.get('detail') or r['outcome']}).")
            return self._answer(state, "REPLAYED" if state.get("replayed") else
                                ("COMPLETED" if r["outcome"] == "COMMITTED" else "FAILED"), text, receipt=r)
        if status in ("CONFLICT", "IN_PROGRESS", "RECOVERY_REQUIRED", "FAILED_FINAL", "FAILED"):
            return self._answer(state, status, f"The request was not executed ({status.lower().replace('_', ' ')}).")
        answer = state.get("answer") or {}
        proposal = state.get("proposal") if intent == "PROPOSE" else None
        if proposal:                                     # PROPOSE without an actionable proposal
            return self._answer(state, "COMPLETED", f"No adjustment is proposed: {proposal['reason']}",
                                degraded=True, proposal=proposal, citations=[e["id"] for e in state["evidence"]],
                                gaps=state.get("evidence_gaps") or [])
        degraded = bool(state.get("degraded")) or any(s.get("status") == "FALLBACK" for s in state.get("steps") or []) or \
            bool(state.get("grounding_failure") or state.get("proposal_refused"))
        return self._answer(state, "COMPLETED", answer.get("answer", ""), degraded=degraded,
                            citations=answer.get("citations") or [], verified=answer.get("verified", []),
                            inferred=answer.get("inferred", []), gaps=state.get("evidence_gaps") or [],
                            records_read=[e["id"] for e in state.get("evidence") or []])
