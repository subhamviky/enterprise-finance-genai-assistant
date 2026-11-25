"""Evidence: each fact read from a system of record, with an identifier the answer must cite.

  recon:<line_id>        a reconciliation exception           (reconciliation-service)
  settlement:<id>        a settlement                         (settlement-service)
  event:<event_id>       a settlement event                   (settlement-service's feed)
  order:<order_id>       an order                             (o2c-agent-service)
  audit:<event_id>       an audit finding                     (audit-ai-service)

Only these identifiers may be cited; an answer citing anything else is refused."""
import re
from typing import Any, Dict, List

LINE_ID = re.compile(r"\b(?:bank\s+)?line\s+([A-Za-z0-9][A-Za-z0-9_.:-]{0,39})\b", re.I)
SETTLEMENT_ID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
ORDER_ID = re.compile(r"\bORD-[A-Z0-9]{10}\b")


def item(kind: str, key: str, summary: str, data: Any) -> Dict[str, Any]:
    return {"id": f"{kind}:{key}", "source": kind, "summary": summary, "data": data}


def ids(evidence: List[Dict[str, Any]]) -> List[str]:
    return [e["id"] for e in evidence]


def find(evidence: List[Dict[str, Any]], kind: str) -> List[Dict[str, Any]]:
    return [e for e in evidence if e["source"] == kind]


def as_text(evidence: List[Dict[str, Any]]) -> str:
    """The evidence as the model sees it: one block per item, its identifier first. Retrieved text
    is data: the firewall has screened the query, and the prompt says the blocks are not instructions."""
    return "\n".join(f"[{e['id']}] {e['summary']}" for e in evidence)
