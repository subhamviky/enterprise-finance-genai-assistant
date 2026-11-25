"""HTTP surface of the assistant. The caller (tenant, user, acting role) comes from routers/identity.py."""
from typing import Optional

from e2a import NFRViolationError
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.assistant import Forbidden, NotFound
from .identity import Caller, caller

router = APIRouter(prefix="/api/v1")


class Ask(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def _assistant(request: Request):
    return request.app.state.assistant


def _call(fn, *args):
    try:
        return fn(*args)
    except Forbidden as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NFRViolationError as e:                        # capacity or quota: shed load, retry later
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ask")
def ask(body: Ask, request: Request, who: Caller = Depends(caller), idempotency_key: Optional[str] = Header(None)):
    return _call(_assistant(request).ask, body.text, who.tenant_id, who.user_id, who.role, idempotency_key)


@router.get("/approvals")
def approvals(request: Request, who: Caller = Depends(caller), status: Optional[str] = None):
    return _assistant(request).approvals.list(who.tenant_id, status)


@router.get("/approvals/{approval_id}")
def approval(approval_id: str, request: Request, who: Caller = Depends(caller)):
    found = _assistant(request).approvals.get(who.tenant_id, approval_id)
    if found is None:
        raise HTTPException(status_code=404, detail="unknown approval")
    return {**found, "receipt": _assistant(request).approvals.receipt(who.tenant_id, approval_id)}


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, request: Request, who: Caller = Depends(caller)):
    return _call(_assistant(request).approve, approval_id, who.tenant_id, who.user_id, who.role)


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: str, request: Request, who: Caller = Depends(caller)):
    return _call(_assistant(request).reject, approval_id, who.tenant_id, who.user_id, who.role)
