# Changelog

All notable changes, newest first. Format: [Keep a Changelog](https://keepachangelog.com). The assistant is released by commit and Cloud Run revision, not by version number, so entries are grouped by the plan's phases and dated by the day the change merged.

## [Unreleased] 28 to 29 November 2026 (Phase C and records)
### Added
- Engineering records: architecture decision records, post-incident reviews, threat model, data classification, SLO policy, incident response, release process, disaster recovery, cost and capacity, teardown plan, test strategy, API reference, requirements and user stories, solution overview, onboarding (`docs/engineering/`).
- Answers from the customer's documents: the `POLICY` intent, tenant-scoped BM25 passages, and a CI check that documents agree with the enforced policy.
- A JSON log line per answer and two log-based metrics (`assistant_answers`, `assistant_tokens`).
- Intent read by rules for plain requests (one model call fewer); `landscape/measure.py` to count calls, tokens and seconds.
- 45 adversarial tests.
- `promote` workflow: canary, gate, automatic rollback; `landscape-gcp` is now reusable as the gate.
- Two simulated customers from configuration (Acme Retail, Globex Logistics); tenant isolation over 24 tenants and a per-tenant in-flight share.
### Changed
- Firewall patterns tolerate extra whitespace and filler words ("ignore   the above instructions").
### Fixed
- `promote`: the previous-revision output came from the wrong step.

## 27 November 2026 (Phase B: reliability and operations)
### Added
- One correlation id through all five services; `landscape/trace_check.sh`.
- SLOs and fast-burn alerts as Terraform (`landscape/observability`).
- Failure drills 1 to 4 on the real cloud and the failure matrix in CI; approval recovery and expiry (410).
- `ops` workflow (deploy any service, close stale open items) from a button.
- Multi-trial live evaluation with fact-based scorers; model comparison.
### Fixed
- The scenario no longer drains the ledger (alternating payer) or the stock (daily restock); reconciliation consumes the open item it closes; Trivy finding (no `pip` in the runtime image); scorer counts model failures as fallbacks; settlement connection timeout 5 s.

## 26 November 2026 (Phase A: correctness)
### Added
- Close the lifecycle: an approved write-off closes the reconciliation exception, with a ledger read-back; the proposal check requires the exact gap and a candidate settlement.

## 25 November 2026 (GCP-01: the landscape on Google Cloud)
### Added
- The assistant (intent, evidence, investigation, proposal, execution agents; four-eyes approval; grounded answers), its policy and governance, 53 golden and 9 red-team cases, Terraform, CI, and the cloud scenario passing against the deployed services.
