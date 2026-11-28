# Threat model: the assistant and its landscape

- **Status:** Reviewed 2026-11-28 · **Method:** STRIDE per trust boundary, plus the LLM-specific threats (OWASP Top 10 for LLM applications) · **Scope:** `genai-assistant-service` and how it reaches the four systems (settlement, reconciliation, audit-ai, O2C) on Google Cloud. Reference implementation on synthetic data: see [data classification](data-classification.md).

## 1. What we protect (assets)

| Asset | Why it matters |
|---|---|
| The ledger (settlement-service's PostgreSQL) | money records; a wrong posting is the worst outcome |
| The approval record and the idempotency claim | they decide whether an adjustment is posted, and once |
| Tenant separation | one customer must never read or approve another's records |
| The Gemini API key and the service identities | abuse costs quota (free tier) and could impersonate a person |
| The audit trail (correlation id, receipts, audit-ai findings) | accountability |

## 2. Trust boundaries and actors

```
 person / scenario account ──(Google ID token)──▶ [Cloud Run IAM] ──▶ genai-assistant-service
                                                                         │ (service ID token, per call)
          Gemini API (external, key from Secret Manager) ◀───────────────┤
          Firestore (state) ◀────────────────────────────────────────────┤
          settlement / reconciliation / audit-ai / O2C (private Cloud Run) ◀┘
 GitHub Actions ──(Workload Identity Federation)──▶ deployer SA ──▶ Cloud Run, Artifact Registry, Terraform-managed resources
```

Actors: an investigator, an approver, an operator (the owner), a hostile caller (authenticated or not), a hostile or confused model, hostile content inside a record or document, a hostile payer who controls a bank-line reference, a compromised database host.

## 3. Threats and controls

| # | Threat (STRIDE) | Where | Control | Evidence |
|---|---|---|---|---|
| T1 | **Spoofing**: calling as someone else | ingress | every service is private; Cloud Run IAM verifies the Google ID token; tenant and roles come from the deployment's grants, never from the request; fail-closed (401/403) | `routers/identity.py`, `tests/test_api.py` |
| T2 | **Spoofing**: a service calls another as itself | service to service | each service attaches its own ID token; the callee's IAM grants only what is listed | SI-01 (landscape identity stack) |
| T3 | **Tampering**: a model drafts an unauthorised adjustment (prompt injection) | proposal | the model cannot post; policy checks (limits, currency, settlement in evidence and COMPLETED, exact gap, not ambiguous) run in code; a second person with the approver role approves; posting is idempotent and read back | `tests/test_adversarial.py` (45 cases), `tests/test_failure_matrix.py`, ADR 0007 |
| T4 | **Tampering**: injection in the request | firewall | patterns tolerant of spacing and filler, length limit; the firewall is the first line, never the only control | post-incident review 0010 |
| T5 | **Tampering**: injection inside a record or document | evidence | retrieved text is evidence, not instruction: the prompt says so, answers must cite what was read, figures must occur in it; the agent's tools are an allow-list; tests plant instructions in a record and a document | `test_adversarial.py`, `test_documents.py` |
| T6 | **Tampering**: a path or query smuggled in an identifier | tools | tool arguments are validated (no `/ ? # % \` and a length cap); identifiers must occur in the request | `tools/catalog.py`, adversarial tests |
| T7 | **Repudiation**: "I did not approve that" | approval | the approval records requester and approver(s) and the receipt names them; one JSON log line per request with a correlation id | `ApprovalStore`, ADR 0016 |
| T8 | **Information disclosure**: cross-tenant read | state, tools, documents | every store key and every search is tenant-scoped; documents of one tenant are invisible to another; 24-tenant isolation test | `tests/test_isolation.py`, `test_documents.py` |
| T9 | **Information disclosure**: personal data in answers or logs | output, logs | IBAN, card, e-mail (and per customer US phone and account) are masked on the way out; the metric line holds no question text and no user | governance redaction, ADR 0022 |
| T10 | **Information disclosure**: secrets | repo, images | no key exists for CI (WIF); the Gemini key is a Secret Manager secret; the runtime image has no `pip`; the vulnerability scan blocks delivery | ADR 0005, 0020 |
| T11 | **Denial of service**: one tenant fills capacity | assistant | per-instance, per-tenant in-flight share; over-limit gets a retryable 503 | ADR 0012 |
| T12 | **Denial of service**: quota exhaustion on the free model | model | every call is bounded; a 429/503 degrades to the verified facts; live runs stop on a 429 | ADR 0006 |
| T13 | **Elevation of privilege**: a role acts as approver, or the requester approves their own | approval | the decider must hold the customer's approver role and differ from the requester; several approvers must be distinct | `_authorize_decision`, `test_customers.py` |
| T14 | **Elevation of privilege**: a compromised database host reads or deletes backups | backups | the VM's account can create backup objects only; restoring is an operator act | post-incident review 0007 |
| T15 | **Elevation of privilege**: abuse of the deployer | CI | WIF restricted to the owner's repositories; the deployer cannot read logs; at teardown the provider and secrets are deleted | ADR 0005 |
| T16 | **LLM**: excessive agency | agents | per-agent tool allow-lists and entitlements; the only material tool is the execution agent's, after approval | `policies/governance.yaml` |
| T17 | **LLM**: overreliance on a wrong answer | answers | grounding rule; `verified` versus `inferred`; the deterministic fallback states facts only | ADR 0009 |

## 4. Residual risks and what is not covered

- **Model behaviour is not guaranteed.** The controls hold whatever the model says, but a model can refuse to help (visible as `fallback`), or phrase misleadingly within the evidence.
- **Indirect injection is tested with planted strings, not with a corpus of real attacks.** The suite grows with findings.
- **The deployer is over-privileged for a demo** (run.admin, datastore.owner, storage.admin, compute.admin, pubsub.admin, secretmanager.admin and others). Acceptable for a short-lived synthetic project; not for production.
- **One tenant per deployment for the other four services** (ADR 0013): isolation across tenants is proven on the assistant with stand-ins, not on the live ledger.
- **No penetration test, no WAF, no DDoS protection beyond Cloud Run's defaults;** services are never public.
- **Supply chain:** dependencies are pinned and the image is scanned, but there is no SBOM-based policy gate and no signature verification of base images.

## 5. Review

Revisit when a service becomes public, real data is introduced, a second customer runs on the live cloud, or a new tool with write access is added.
