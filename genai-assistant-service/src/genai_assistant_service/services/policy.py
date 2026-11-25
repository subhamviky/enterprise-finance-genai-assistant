"""policies/governance.yaml, parsed once: entitlements, tool allow-lists, adjustment limits,
approval, firewall, redaction and capacity. Code reads policy from here, never from a prompt."""
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from e2a import compile_redactions, redact_text

POLICY_FILE = Path(__file__).resolve().parents[3] / "policies" / "governance.yaml"


class Policy:
    def __init__(self, path: Optional[Path] = None) -> None:
        data = yaml.safe_load(Path(path or POLICY_FILE).read_text(encoding="utf-8"))
        self.entitlements: Dict[str, List[str]] = data["entitlements"]
        self.tools: Dict[str, List[str]] = data["tools"]
        self.limits: Dict[str, Decimal] = {k: Decimal(v["max_amount"]) for k, v in data["adjustments"].items()}
        self.approver_role: str = data["approval"]["approver_role"]
        self.four_eyes: bool = bool(data["approval"]["four_eyes"])
        self.injection_patterns: List[str] = data["firewall"]["injection_patterns"]
        self.max_query_chars = int(data["firewall"]["max_query_chars"])
        self.redaction = compile_redactions(data["redaction"])
        self.max_inflight = int(data["capacity"]["max_inflight"])
        self.max_token_budget = float(data["capacity"]["max_token_budget"])

    def redact(self, text: str) -> str:
        return redact_text(text, self.redaction)[0]

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
        if proposal.get("currency") != settlement.get("currency"):
            return f"currency {proposal.get('currency')} differs from the settlement's {settlement.get('currency')}"
        if settlement.get("status") != "COMPLETED":
            return f"settlement is {settlement.get('status')}; only a COMPLETED settlement is adjusted"
        if not str(proposal.get("reason") or "").strip() or len(str(proposal.get("reason"))) > 500:
            return "a reason (at most 500 characters) is required"
        return None
