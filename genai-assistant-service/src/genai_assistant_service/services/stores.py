"""The approvals: E2A's checkpoint store (BaseWorkflow saves a paused run here; resume() decides it
exactly once, as one compare-and-set), each checkpoint also listed as an Approval for the API, and
the receipts of executed adjustments. On a BaseTransactionalStore: in memory or Firestore."""
import time
from typing import Callable, Dict, List, Optional

from e2a import BaseCheckpointStore, BaseTransactionalStore

INDEX_LIMIT = 500                        # the newest approvals a tenant's index keeps


class ApprovalStore(BaseCheckpointStore):
    """Approvals on a shared store, with an expiry: a PENDING approval older than ttl_seconds becomes EXPIRED the
    next time anyone reads or decides it (one compare-and-set, so every instance agrees), and an expired approval
    cannot be approved. There is no timer: expiry is decided at the moment it matters."""

    def __init__(self, db: BaseTransactionalStore, ttl_seconds=None,
                 clock: Callable[[], float] = time.time) -> None:
        """ttl_seconds: a number, or a function of the tenant id (each customer's own window)."""
        self._db, self._clock = db, clock
        self._ttl = ttl_seconds if callable(ttl_seconds) else (lambda tenant: ttl_seconds)

    def _due(self, raw: Dict) -> bool:
        created, ttl = raw["approval"].get("created_at"), self._ttl(raw["approval"]["tenant_id"])
        return (ttl is not None and raw["approval"]["status"] == "PENDING" and created is not None
                and self._clock() - created > ttl)

    def _expire_if_due(self, key: str) -> Optional[Dict]:
        """The stored record, expired first if it is due. The change is a compare-and-set: if another instance
        decides or expires it at the same moment, this one simply re-reads."""
        for _ in range(5):
            current = self._db.get_versioned(key)
            if current is None:
                return None
            raw, version = current
            if not self._due(raw):
                return raw
            expired = {"approval": dict(raw["approval"], status="EXPIRED", decided_by="system:expired"),
                       "checkpoint": dict(raw["checkpoint"], status="EXPIRED")}
            if self._db.put_if_version(key, expired, version).committed:
                return expired
        return self._db.get(key)

    def save(self, checkpoint, config=None, **kwargs) -> None:
        state = checkpoint["state"]
        approval = {"approval_id": checkpoint["checkpoint_id"], "tenant_id": checkpoint["tenant_id"],
                    "requested_by": checkpoint["requested_by"], "status": "PENDING",
                    "proposal": state.get("proposal"), "query": state.get("query"),
                    "citations": [e["id"] for e in state.get("evidence") or []], "decided_by": None,
                    "created_at": self._clock(), "approvers": []}
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
        raw = self._expire_if_due(f"approval:{checkpoint_id}")
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

    def add_approver(self, tenant_id: str, approval_id: str, approver: str) -> Optional[List[str]]:
        """Record one approver of a multi-step approval, as one compare-and-set, and return everyone who has approved
        so far (including this one). None when the approval is not PENDING any more (decided, rejected or expired).
        Approving twice is the same as approving once."""
        key = f"approval:{approval_id}"
        for _ in range(10):
            raw = self._expire_if_due(key)
            if raw is None or raw["approval"]["tenant_id"] != tenant_id or raw["approval"]["status"] != "PENDING":
                return None
            current = self._db.get_versioned(key)
            if current is None:
                return None
            raw, version = current
            approvers = list(raw["approval"].get("approvers") or [])
            if approver in approvers:
                return approvers
            updated = {"approval": dict(raw["approval"], approvers=approvers + [approver]), "checkpoint": raw["checkpoint"]}
            if self._db.put_if_version(key, updated, version).committed:
                return approvers + [approver]
        raise RuntimeError(f"approval {approval_id} is contended; retry")

    def get(self, tenant_id: str, approval_id: str) -> Optional[Dict]:
        raw = self._expire_if_due(f"approval:{approval_id}")
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
