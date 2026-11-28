# Requirements and user stories

- **Status:** Draft 2026-11-28, awaiting owner review · The design document (`docs/design/GENAI_ASSISTANT_DESIGN.md`, section 2) traces requirements to the design; this document states them from the users' side, with acceptance criteria that are tests.

## Personas

| Persona | Goal |
|---|---|
| **Investigator (Ana)** | understand why a payment is unmatched or a settlement delayed, and get a safe proposal to fix it |
| **Approver (Bo)** | decide a proposed adjustment quickly, knowing what it is and that nothing was posted yet |
| **Customer administrator** | have the assistant follow the customer's limits, currencies, roles and documents |
| **Operator** | ship changes safely, see when the model is not doing the work, recover from failures |
| **Auditor** | reconstruct who asked, who approved, what was posted and why |

## Stories and acceptance criteria

| # | As a... | I want... | So that... | Acceptance (verified by) |
|---|---|---|---|---|
| U1 | investigator | to ask why bank line L-1001 is unmatched | I find the cause without opening four systems | the answer cites the bank line, the exception and the settlement and states the exact shortfall; nothing is written (`test_journeys.py`, live trial `investigate_cites_what_it_read`) |
| U2 | investigator | to ask why a settlement was flagged or an order was not paid | I see verified facts separately from the assistant's reasoning | `verified` and `inferred` are separate; every cited id was read (`test_journeys.py`) |
| U3 | investigator | to ask for a write-off or refund on a line | the fix is prepared for me | a proposal appears for the right settlement and the exact gap, or the assistant says why not (`propose_writeoff`, `test_failure_matrix.py`) |
| U4 | investigator | to be told when a request exceeds the limit | I do not wait for an approval that cannot happen | an over-limit proposal is never offered (`over_limit_is_never_offered`) |
| U5 | approver | to approve a proposal made by someone else | no one approves their own money movement | the requester cannot approve; only the approver role can; with two required approvers, both must be distinct (`test_customers.py`) |
| U6 | approver | the posting to happen exactly once, even if I click twice | the ledger stays right | replayed and concurrent approvals post once; the ledger is balanced and the posting is read back (`test_failure_matrix.py`, cloud scenario steps 7 to 10) |
| U7 | approver | an unanswered proposal to lapse | stale proposals cannot be posted later | after the window the answer is 410 and nothing is posted (`test_approval_recovery.py`) |
| U8 | investigator | the exception to close after the posting | I do not do it by hand | reconciliation closes it only if the ledger shows the adjustment; if it cannot, the receipt says so (`test_failure_matrix.py`) |
| U9 | customer administrator | limits, currencies, approver roles, number of approvers and the decision window from a file | onboarding a customer is configuration | two customers behave differently through one service (`test_customers.py`) |
| U10 | customer administrator | questions about our rules answered from our documents | people get the policy right, with a citation | a policy question cites our document, a figure not in the document is refused, and documents agree with the enforced policy (`test_documents.py`) |
| U11 | customer administrator | no customer to see another's data or crowd it out | I can trust the service | 24-tenant isolation; a noisy tenant is refused while a quiet one is served (`test_isolation.py`) |
| U12 | investigator | personal data masked in answers | I do not copy an IBAN into a ticket | IBAN, card and e-mail (and a customer's extra patterns) are masked (`test_safety.py`) |
| U13 | operator | a deliberately hostile request to cause no action | the assistant cannot be talked into posting | 45 adversarial cases (`test_adversarial.py`) |
| U14 | operator | a bad release to be undone automatically | a mistake does not reach every user | a failed gate restores the previous revision (Drill 6) |
| U15 | operator | to see when the model is not doing the work | I know when quality has dropped | `assistant_answers` by `degraded`; the multi-trial report (`landscape/observability`) |
| U16 | auditor | to follow one request through all services | I can reconstruct what happened | one correlation id appears in every service's log (`trace_check.sh`) |
| U17 | operator | recovery from a stopped ledger, a stalled feed, a lost backup and a mid-approval redeploy | outages are boring | the four drills' recorded recoveries (`docs/DRILL_RESULTS.md`) |

## Non-functional requirements

| Area | Requirement | Where |
|---|---|---|
| Cost | zero; free tier only; never upgrade | ADR 0001, [cost and capacity](../operations/cost-and-capacity.md) |
| Availability | 99% non-5xx per service over 28 days; the model is optional (the system degrades to facts) | [SLO policy](../operations/slo-and-error-budget.md) |
| Security | private services, verified identity, no keys, least-privilege tools | [threat model](../security/threat-model.md) |
| Data | synthetic only | [data classification](../security/data-classification.md) |
| Auditability | who asked, who approved, what posted, one id across services | design section 10, ADR 0016 |
| Operability | button-driven deploy and promote; runbook; drills | [release process](../operations/release-process.md) |

## Out of scope

Real customer data, a user interface, multiple regions, real-time streaming, other currencies than those a customer allows, automatic approval of any adjustment.
