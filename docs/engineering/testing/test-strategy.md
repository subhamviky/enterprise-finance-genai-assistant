# Test strategy

- **Status:** Draft 2026-11-28, awaiting owner review · **Scope:** the assistant (the other repositories have their own strategy documents that follow the same layers).

## Principles

1. **Test the property, not the wording.** A live model is not deterministic, so scorers check facts in the systems (what was posted, on which settlement, for how much, whether the exception closed, whether anything was written before the approval), never phrases.
2. **A green result must be able to be red.** A scorer that passes when the model never answered was a defect (post-incident review 0006); a trial with model errors counts as a fallback, not a pass.
3. **The model is the attacker.** Safety tests make the model draft what an injected prompt would make it draft, and check what is posted. Controls are structural, so they must hold whatever the model says.
4. **Every live finding becomes a regression test.** The adversarial suite and the failure matrix grow from drills and live runs.
5. **Finite resources are a test-design concern.** A scenario must not consume what it cannot restore (ADR 0019).

## The layers

| Layer | What it proves | Where | Runs |
|---|---|---|---|
| Unit and contract | agents' accept/refuse rules, policy checks, stores (compare-and-set, expiry with a clock), tools' argument validation, generated contract and workflow tests | `tests/test_*.py` | every push, locally and in CI |
| Journeys | investigate, explain (settlement and order), propose and approve, replay, against stand-ins of the four systems | `test_journeys.py`, `test_workflow.py` | every push |
| Failure matrix | model unavailable (429/503), fenced or unreadable replies, replayed and concurrent approvals post once, settlement outage, reconciliation outage, changed settlement, wrong candidate, ambiguity | `test_failure_matrix.py`, `test_approval_recovery.py` | every push |
| Adversarial | 45 cases: injection phrasings, oversize and malformed input, a model drafting hostile adjustments (negative, NaN, wrong currency, wrong settlement, over the limit), instructions hidden in records and documents, hostile callers | `test_adversarial.py`, `test_safety.py` | every push |
| Customers and isolation | two customers' policies through one service; 24 tenants with no cross read or approval; a noisy-neighbour test with an async gate | `test_customers.py`, `test_isolation.py` | every push |
| Intent by rules and documents | the optimisation does not change what is safe; documents rank, are tenant-scoped, agree with the policy, and a poisoned document is data | `test_intent_by_rules.py`, `test_documents.py` | every push |
| Emulator pass | the same tests with state in the Firestore emulator (the real binding) | CI step | every push |
| Conformance | E2A's strict rules (no public-method overrides, no external protected calls) | CI step, `test_conformance.py` | every push |
| Release gate and golden sets | 53 golden cases (investigation, explanation, orders, proposals, approvals, unsupported, unknown ids, outages, cross-tenant) and 9 red-team cases scored by E2A's scorers | `evals/`, CI step, gate report kept as an artifact | every push |
| Infrastructure | Terraform fmt, validate and plan-level tests against a mock provider (SLOs, log-based metrics, stacks) | CI matrix | every push |
| Image | build and vulnerability scan (Trivy) | delivery pipeline | on merge |
| Scenario (local) | the five services on one runner with emulators (Firestore, Pub/Sub, PostgreSQL) | `landscape-gcp`, target `local` | on demand |
| Scenario (cloud) | 14 steps against the deployed services, with real identities | `landscape-gcp`, target `cloud`; also the gate of `promote` | on demand, per promotion |
| Multi-trial live evaluation | fact-based scorers, N trials per case on the live model, outcomes `pass`, `fallback`, `wrong-fact`, `error` | `landscape/live_trials.py` | on demand, one model per day |
| Measurement | model calls, tokens and seconds per agent step, with and without intent-by-rules | `landscape/measure.py` | on demand |
| Failure drills | the ledger VM stops, Pub/Sub pauses, a backup is restored, a redeploy happens mid-approval, a bad candidate is rolled back | `docs/DRILLS.md` | rehearsed, results recorded |

## Entry and exit criteria

- **A pull request merges** when CI is green: all tests, the emulator pass, conformance, the gate, Terraform checks.
- **A change is promoted** when the cloud scenario passes against the candidate (the gate) and again at 100%.
- **A model change is accepted** only with the same cases, scorers and trial count as the model it is compared with, labelled with the model id, the date and the limits it ran under.

## Known gaps

No load or soak test (free-tier limits make one unrepresentative); no mutation testing; no property-based tests of the policy (the limit and currency cases are table-driven); the live model's behaviour is sampled, not covered; the cloud scenario cannot run the requester-approves-own case (step 7a) with one stand-in account (covered locally and in tests).

## Metrics we look at

Pass rate per case and its failure classes (not a single score); the degraded-answer rate; tokens per request; the gate's pass/fail per promotion; the budget remaining on each SLO.
