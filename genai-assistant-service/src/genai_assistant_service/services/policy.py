"""policies/governance.yaml, parsed once: entitlements, tool allow-lists, adjustment limits,
approval, firewall, redaction and capacity. Code reads policy from here, never from a prompt."""
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from e2a import compile_redactions, redact_text

POLICY_FILE = Path(__file__).resolve().parents[3] / "policies" / "governance.yaml"
CUSTOMERS_DIR = Path(__file__).resolve().parents[3] / "policies" / "customers"


class Policy:
    def __init__(self, path: Optional[Path] = None) -> None:
        data = yaml.safe_load(Path(path or POLICY_FILE).read_text(encoding="utf-8"))
        self.entitlements: Dict[str, List[str]] = data["entitlements"]
        self.tools: Dict[str, List[str]] = data["tools"]
        self.limits: Dict[str, Decimal] = {k: Decimal(v["max_amount"]) for k, v in data["adjustments"].items()}
        self.approver_role: str = data["approval"]["approver_role"]
        self.four_eyes: bool = bool(data["approval"]["four_eyes"])
        self.approval_ttl_seconds: int = int(float(data["approval"].get("expires_after_hours", 24)) * 3600)
        self.injection_patterns: List[str] = data["firewall"]["injection_patterns"]
        self.max_query_chars = int(data["firewall"]["max_query_chars"])
        self._redaction_spec = list(data["redaction"])
        self.redaction = compile_redactions(self._redaction_spec)
        self.max_inflight = int(data["capacity"]["max_inflight"])
        self.max_token_budget = float(data["capacity"]["max_token_budget"])
        self.customer: Optional[str] = None
        self.currencies: Optional[List[str]] = None        # None: any currency the settlement has
        self.approvals_required: int = int(data["approval"].get("approvals_required", 1))

    def for_customer(self, overrides: Dict) -> "Policy":
        """This policy with one customer's file laid over it: only the sections the file names change (entitlements
        replace the base's; adjustments, approval and redaction_add are merged), everything else stays the base."""
        import copy
        custom = copy.copy(self)
        custom.customer = overrides.get("customer")
        if overrides.get("currencies"):
            custom.currencies = [str(c).upper() for c in overrides["currencies"]]
        if overrides.get("entitlements"):
            custom.entitlements = dict(overrides["entitlements"])
        if overrides.get("adjustments"):
            custom.limits = {**self.limits, **{k: Decimal(v["max_amount"]) for k, v in overrides["adjustments"].items()}}
        approval = overrides.get("approval") or {}
        if "approver_role" in approval:
            custom.approver_role = approval["approver_role"]
        if "four_eyes" in approval:
            custom.four_eyes = bool(approval["four_eyes"])
        if "approvals_required" in approval:
            custom.approvals_required = int(approval["approvals_required"])
        if "expires_after_hours" in approval:
            custom.approval_ttl_seconds = int(float(approval["expires_after_hours"]) * 3600)
        if overrides.get("redaction_add"):
            custom.redaction = compile_redactions(list(self._redaction_spec) + list(overrides["redaction_add"]))
        return custom

    def redact(self, text: str) -> str:
        return redact_text(text, self.redaction)[0]

    @staticmethod
    def check_against_bank_line(proposal: Dict, settlement: Optional[Dict], line: Optional[Dict],
                                case: Optional[Dict], named: Optional[str] = None,
                                settlements: Optional[Dict[str, Dict]] = None) -> Optional[str]:
        """When the request is about a bank line, the adjustment must be the one that line needs: on a settlement
        reconciliation named as a candidate, and for exactly the difference between that settlement and the line
        (a short payment is written off, an overpayment refunded). The model drafts; this decides (GCP-02 A.2:
        a live model once chose another COMPLETED candidate, which the other checks allowed)."""
        action = proposal.get("action")
        if action == "NONE" or not line or not case or not settlement:
            return None
        candidates = {c.get("settlement_id") for c in case.get("candidates") or []}
        if proposal.get("settlement_id") not in candidates:
            return f"settlement {proposal.get('settlement_id')} is not a candidate of bank line {line.get('line_id')}"
        try:
            paid, owed, amount = (Decimal(str(line["amount"])), Decimal(str(settlement["amount"])),
                                  Decimal(str(proposal["amount"])))
        except (InvalidOperation, KeyError, ValueError):
            return "the bank line, the settlement or the amount cannot be compared"
        gap = owed - paid if action == "WRITE_OFF" else paid - owed
        if amount != gap:
            what = "short by" if action == "WRITE_OFF" else "over by"
            return f"{action} of {amount} does not match the bank line, which is {what} {gap} against that settlement"
        if named:                                   # the person said which settlement: that one, nothing else
            return None if proposal.get("settlement_id") == named else \
                f"the request names settlement {named}, not {proposal.get('settlement_id')}"
        fits = [sid for sid, s in (settlements or {}).items() if sid in candidates and s.get("status") == "COMPLETED"
                and (Decimal(str(s["amount"])) - paid if action == "WRITE_OFF" else paid - Decimal(str(s["amount"]))) == amount]
        if len(fits) > 1:
            return (f"{len(fits)} candidate settlements fit this bank line equally ({', '.join(sorted(fits))}): "
                    "name the settlement to adjust")
        return None

    def check_proposal(self, proposal: Dict, settlement: Optional[Dict]) -> Optional[str]:
        """Why a drafted adjustment is not allowed, or None. The model drafts; this decides."""
        action = proposal.get("action")
        if action == "NONE":
            return None
        if action not in self.limits:
            return f"unknown action {action!r}"
        if not settlement:
            return f"settlement {proposal.get('settlement_id')} is not in the evidence"
        try:
            amount = Decimal(str(proposal.get("amount")))
        except (InvalidOperation, ValueError):
            return f"amount {proposal.get('amount')!r} is not a number"
        if amount <= 0 or amount != amount.quantize(Decimal("0.01")):
            return f"amount {amount} must be positive with at most two decimals"
        if amount > self.limits[action]:
            return f"{action} of {amount} exceeds the policy limit {self.limits[action]}"
        if amount > Decimal(str(settlement.get("amount"))):
            return f"{amount} exceeds the settlement amount {settlement.get('amount')}"
        if self.currencies is not None and proposal.get("currency") not in self.currencies:
            return f"currency {proposal.get('currency')} is not accepted for this customer ({', '.join(self.currencies)})"
        if proposal.get("currency") != settlement.get("currency"):
            return f"currency {proposal.get('currency')} differs from the settlement's {settlement.get('currency')}"
        if settlement.get("status") != "COMPLETED":
            return f"settlement is {settlement.get('status')}; only a COMPLETED settlement is adjusted"
        if not str(proposal.get("reason") or "").strip() or len(str(proposal.get("reason"))) > 500:
            return "a reason (at most 500 characters) is required"
        return None


class PolicyBook:
    """The base policy and one Policy per customer (policies/customers/<tenant>.yaml). for_tenant() is what a request
    uses; a tenant with no file gets the base policy."""

    def __init__(self, base: Policy, customers: Optional[Dict[str, Policy]] = None) -> None:
        self.base, self.customers = base, customers or {}

    @classmethod
    def of(cls, policy_or_book) -> "PolicyBook":
        if isinstance(policy_or_book, PolicyBook):
            return policy_or_book
        return cls(policy_or_book or Policy())

    @classmethod
    def load(cls, base_path: Optional[Path] = None, customers_dir: Optional[Path] = None) -> "PolicyBook":
        base = Policy(base_path)
        folder = Path(customers_dir or CUSTOMERS_DIR)
        customers = {}
        for file in sorted(folder.glob("*.yaml")) if folder.is_dir() else []:
            data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
            customers[str(data.get("tenant") or file.stem)] = base.for_customer(data)
        return cls(base, customers)

    def for_tenant(self, tenant: Optional[str]) -> Policy:
        return self.customers.get(str(tenant), self.base)
