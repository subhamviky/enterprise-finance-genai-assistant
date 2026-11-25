"""Who is calling: identity at ingress (E2A v1.11.0, hub design note GCP-01).

On Cloud Run, IAM verifies the caller's Google ID token (a person's or a service account's) before
the request reaches the service; e2a-adapters reads it (E2A_IDENTITY_SOURCE=gcp_cloud_run). The token
names only an email, so the deployment grants each caller its tenants ("tenant:<id>") and roles
(E2A_IDENTITY_SUBJECT_ROLES); the caller names the tenant in X-Tenant-Id and may choose its acting
role in X-User-Role (by default its first role that is not a tenant grant). Fail-closed: no verified
token 401; an ungranted tenant or role 403.

Local mode (E2A_IDENTITY_SOURCE unset: tests, local runs, the landscape stand-ins) takes X-Tenant-Id,
X-User-Id and X-User-Role as given."""
import os
from dataclasses import dataclass

from e2a import IdentityRefused
from fastapi import Header, HTTPException, Request


@dataclass(frozen=True)
class Caller:
    tenant_id: str
    user_id: str
    role: str


def _config() -> dict:
    from e2a_adapters.identity import preset
    source = os.getenv("E2A_IDENTITY_SOURCE") or None
    cfg = {"identity_source": source}
    if source == "gcp_cloud_run":
        cfg.update({"identity_claim_map": preset("google_id_token"), "identity_tenants_from_roles": "tenant:"})
    return cfg


def caller(request: Request, x_tenant_id: str = Header(""), x_user_id: str = Header(""),
           x_user_role: str = Header("")) -> Caller:
    from e2a_adapters.ingress import identity_at_ingress
    try:
        identity = identity_at_ingress(_config(), headers=request.headers, request_tenant=x_tenant_id or None)
    except IdentityRefused as refused:
        raise HTTPException(status_code=401 if "not verified" in str(refused) else 403, detail=str(refused))
    except ValueError as malformed:
        raise HTTPException(status_code=401, detail=str(malformed))
    if identity is None:                                      # local mode
        return Caller(x_tenant_id, x_user_id, x_user_role)
    if x_user_role and x_user_role not in identity.roles:
        raise HTTPException(status_code=403, detail=f"the credentials do not carry the role {x_user_role!r}")
    acting = [r for r in identity.roles if not r.startswith("tenant:")]
    return Caller(identity.tenant_id, identity.subject or "", x_user_role or (acting[0] if acting else ""))
