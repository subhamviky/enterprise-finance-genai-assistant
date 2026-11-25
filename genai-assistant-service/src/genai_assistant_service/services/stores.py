"""The approvals: E2A's checkpoint store (BaseWorkflow saves a paused run here; resume() decides it
exactly once, as one compare-and-set), each checkpoint also listed as an Approval for the API, and
the receipts of executed adjustments. On a BaseTransactionalStore: in memory or Firestore."""
from typing import Dict, List, Optional

from e2a import BaseCheckpointStore, BaseTransactionalStore

INDEX_LIMIT = 500                        # the newest approvals a tenant's index keeps


class ApprovalStore(BaseCheckpointStore):
    def __init__(self, db: BaseTransactionalStore) -> None:
        self._db = db

    def save(self, checkpoint, config=None, **kwargs) -> None:
        state = checkpoint["state"]
        approval = {"approval_id": checkpoint["checkpoint_id"], "tenant_id": checkpoint["tenant_id"],
                    "requested_by": checkpoint["requested_by"], "status": "PENDING",
                    "proposal": state.get("proposal"), "query": state.get("query"),
                    "citations": [e["id"] for e in state.get("evidence") or []], "decided_by": None}
        if self._db.put_if_version(f"approval:{approval['approval_id']}",
                                   {"approval": approval, "checkpoint": checkpoint}, None).committed:
            self._index(approval["tenant_id"], approval["approval_id"])

    def _index(self, tenant_id: str, approval_id: str) -> None:
        key = f"approvals:{tenant_id}"
        for _ in range(20):                                  # compare-and-set: every instance sees the same list
            current = self._db.get_versioned(key)
            ids, version = (current[0]["ids"], current[1]) if current else ([], None)
            if self._db.put_if_version(key, {"ids": (ids + [approval_id])[-INDEX_LIMIT:]}, version).committed:
                return
        raise RuntimeError(f"approval index of {tenant_id} is contended; retry")

    def load(self, checkpoint_id, config=None, tenant_id=None, **kwargs):
        raw = self._db.get(f"approval:{checkpoint_id}")
        if raw is None or raw["checkpoint"]["tenant_id"] != tenant_id:
            return None
        return dict(raw["checkpoint"], status=raw["approval"]["status"])

    def decide(self, checkpoint_id, status, decided_by, config=None, **kwargs) -> bool:
        current = self._db.get_versioned(f"approval:{checkpoint_id}")
        if current is None or current[0]["approval"]["status"] != "PENDING":
            return False
        raw, version = current
        decided = {"approval": dict(raw["approval"], status=status, decided_by=decided_by),
                   "checkpoint": dict(raw["checkpoint"], status=status)}
        return self._db.put_if_version(f"approval:{checkpoint_id}", decided, version).committed

    def get(self, tenant_id: str, approval_id: str) -> Optional[Dict]:
        raw = self._db.get(f"approval:{approval_id}")
        return raw["approval"] if raw and raw["approval"]["tenant_id"] == tenant_id else None

    def list(self, tenant_id: str, status: Optional[str] = None) -> List[Dict]:
        index = self._db.get(f"approvals:{tenant_id}") or {"ids": []}
        rows = [self.get(tenant_id, a) for a in index["ids"]]
        return [a for a in rows if a is not None and (status is None or a["status"] == status)]

    def record_receipt(self, tenant_id: str, approval_id: str, receipt: Dict) -> None:
        """The executed adjustment's receipt, kept with its approval (audit metadata)."""
        key = f"receipt:{tenant_id}:{approval_id}"
        if self._db.get(key) is None:
            self._db.put_if_version(key, receipt, None)

    def receipt(self, tenant_id: str, approval_id: str) -> Optional[Dict]:
        return self._db.get(f"receipt:{tenant_id}:{approval_id}")
