# API reference: genai-assistant-service

- **Status:** Draft 2026-11-28, awaiting owner review · **Source of truth:** `genai-assistant-service/src/genai_assistant_service/routers/api.py`; FastAPI also serves `/openapi.json` and `/docs` from a running service. Base path `/api/v1`. All routes are private: on Cloud Run IAM verifies the caller's Google ID token before the request arrives.

## Calling convention

| Header | Required | Meaning |
|---|---|---|
| `Authorization: Bearer <Google ID token>` | on Cloud Run | audience is the service URL (the same token is accepted on a revision's tag URL) |
| `X-Tenant-Id` | yes | the customer; must be one the caller is granted (`tenant:<id>`), else 403 |
| `X-User-Role` | optional | the acting role (default: the caller's first role that is not a tenant grant) |
| `X-Correlation-Id` | optional | kept and returned; one is created if absent; send it on every call of a run to follow it through the five services |
| `Idempotency-Key` | optional on `/ask` | the same key and the same request replays the original outcome; without one, the same proposal by the same person is one adjustment |

In local mode (no identity source set: tests and stand-ins) `X-Tenant-Id`, `X-User-Id` and `X-User-Role` are taken as given.

## Endpoints

### `GET /health`
Liveness. `200 {"status": "ok"}`. Not authenticated by the service (IAM still applies on Cloud Run).

### `POST /api/v1/ask`
Ask a question or request an action. Body: `{"text": "..."}` (1 to 4000 characters).

Intents: `INVESTIGATE`, `EXPLAIN`, `PROPOSE`, `POLICY`, `UNSUPPORTED`.

Example, an investigation:
```json
POST /api/v1/ask   {"text": "Why is bank line L-1001 unmatched?"}
200 {"status": "COMPLETED", "intent": "INVESTIGATE",
     "answer": "Bank statement line L-1001: 171.00 EUR ... short by 12.50 ...",
     "citations": ["recon:L-1001", "line:L-1001", "settlement:<id>"],
     "verified": ["..."], "inferred": ["The difference is most likely a bank fee or a short payment by the payer."],
     "records_read": ["recon:L-1001", "line:L-1001", "settlement:<id>"],
     "gaps": [], "degraded": false, "correlation_id": "..."}
```

Example, a proposal (nothing is posted):
```json
POST /api/v1/ask   {"text": "Propose a write-off for bank line L-1001"}
200 {"status": "AWAITING_APPROVAL", "intent": "PROPOSE", "approval_id": "<id>",
     "proposal": {"action": "WRITE_OFF", "settlement_id": "<id>", "amount": "12.50", "currency": "EUR", "reason": "..."},
     "answer": "Proposed WRITE_OFF of 12.50 EUR on settlement <id>: ... It waits for a finance-approver other than you (approval <id>); nothing has been posted.",
     "citations": ["..."], "correlation_id": "..."}
```

Example, a question about the customer's rules:
```json
POST /api/v1/ask   {"text": "What is the write-off limit?"}
200 {"status": "COMPLETED", "intent": "POLICY",
     "answer": "A write-off may not exceed 250.00 EUR ...", "citations": ["doc:acme/write-off-policy#limits"], ...}
```

`status` values: `COMPLETED`, `AWAITING_APPROVAL`, `REFUSED` (the firewall), `NOT_FOUND`, `REPLAYED`, `FAILED`, `IN_PROGRESS`, `CONFLICT`, `RECOVERY_REQUIRED`. `degraded: true` means the deterministic fallback replaced the model; the answer then states verified facts only.

### `GET /api/v1/approvals[?status=...]`
The caller's tenant's approvals (newest 500).

### `GET /api/v1/approvals/{approval_id}`
One approval with its receipt (outcome, adjustment id, read-back, approver(s)). `404` if unknown to the tenant.

### `POST /api/v1/approvals/{approval_id}/approve`
Approve. The caller must hold the customer's approver role and must not be the requester (four eyes); with several approvers required, each distinct approver is recorded and the adjustment posts when the last one needed has approved. Returns `status: COMPLETED` with a `receipt` (`outcome`, `adjustment_id`, `read_back`, `exception` closure) or `AWAITING_APPROVAL` while more approvers are needed.

### `POST /api/v1/approvals/{approval_id}/reject`
Reject. Nothing is posted. `{"status": "REJECTED", ...}`.

## Errors

| Code | Meaning |
|---|---|
| 400 | invalid request (for example an empty question) |
| 401 | no verified identity (on Cloud Run: IAM) |
| 403 | tenant or role not granted, requester cannot approve their own, not the approver role |
| 404 | unknown approval for this tenant |
| 410 | the approval expired; nothing was posted; ask again |
| 422 | body does not match the schema (FastAPI validation) |
| 503 | capacity or quota: retry later (a tenant over its in-flight share, the global limit, the token budget) |

Errors carry `{"detail": "..."}`. Responses always carry `X-Correlation-Id`.

## Guarantees and limits

An adjustment is posted once (idempotent keys end to end), only after a valid proposal and a second person's approval, and is read back from the ledger. Answers cite only records that were read. Limits come from the customer's policy (Acme: write-off 250.00 EUR, refund 1000.00 EUR; Globex: 1000.00 and 5000.00 USD with two approvers). The service is not rate-limited per user beyond the per-tenant in-flight share. No versioning policy beyond `/api/v1`: a breaking change would add `/api/v2`.
