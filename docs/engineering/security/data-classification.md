# Data classification and handling

- **Status:** Reviewed 2026-11-28 · **Applies to:** the whole landscape (assistant, settlement, audit-ai, reconciliation, O2C).

## Rule

**All data is synthetic.** No real customer, payment, account, person or document may be put into this landscape (`SECURITY.md`, ADR 0002). The controls below exist so that the behaviour is demonstrated and so the same design could carry real data after a proper review, not because real data is present.

## Data inventory

| Data | Where it lives | Classification if it were real | Retention here | Protection |
|---|---|---|---|---|
| Orders, customers, amounts, currencies | O2C state (Firestore) | Confidential | until teardown | private Cloud Run, tenant-scoped keys |
| Settlements and the ledger | PostgreSQL on an Always Free VM (no external address) | Restricted (financial) | until teardown; daily `pg_dump` in a bucket, restorable | VM account can create backups only; IAP for operators; secrets in Secret Manager |
| Bank lines, payer account references, open items | reconciliation state (Firestore) | Restricted | until teardown | private; one tenant per deployment |
| Audit findings (risk, rule hits) | audit-ai state | Confidential | until teardown | private; Pub/Sub push with signed tokens |
| Approvals, proposals, receipts, idempotency claims | assistant state (Firestore) | Confidential | until teardown (approvals expire after 24 h or 48 h for new decisions; records stay) | tenant-scoped keys, compare-and-set |
| Questions typed to the assistant | request only; sent to the model | Confidential | **not stored**, **not logged** | masked before leaving the service; the per-answer metric line holds none |
| Policy documents of a customer | files in the image | Internal | with the image | tenant scope enforced in search |
| Logs | Cloud Logging | Internal | Cloud Logging default retention | JSON lines hold ids, statuses, counts; no question text or user in the metric line |
| Gemini API key | Secret Manager | Secret | until teardown | not in code, image, state or logs |

## Handling rules

1. **Masking.** IBAN, payment-card numbers and e-mail addresses are masked in answers by default; a customer can add masks (Globex: US phone and bank account numbers).
2. **Model provider.** Requests to the Gemini free tier may be used by the provider to improve its products. This is acceptable only because the data is synthetic; a real deployment needs a provider and a plan with contractual no-training terms and a data-processing agreement.
3. **Identity.** People appear as e-mail addresses of the owner's own accounts and stand-in service accounts. They are not published in documents or sent to external services.
4. **Deletion.** Teardown destroys every stack, deletes the Firestore data, the backup bucket, the secrets and the WIF provider ([teardown](../operations/teardown-and-exit.md)).
5. **Evidence.** Screenshots and logs saved into `docs/assets/evidence` are checked for anything identifying before commit.

## If this ever carried real data

Out of scope here; the minimum would be: classification sign-off, a lawful basis and a records-of-processing entry, a provider contract, a retention schedule, field-level encryption for account numbers, a data-subject-request path, and a security review (see the threat model's residual risks).
