# Architecture Decision Records

One record per significant decision, in the MADR shape (context, options, decision, consequences). A record is never edited to change history: a reversed decision gets a new record that supersedes the old one, and the old one's status becomes `Superseded by NNNN`. The records below were written from the project's history (design notes, pull requests, drills and failures), so their dates name the phase, not the day of a meeting.

Template: [`0000-template.md`](0000-template.md).

| # | Decision | Status |
|---|---|---|
| [0001](0001-run-landscape-real-google-cloud-free-tier.md) | Run the landscape on the real Google Cloud free tier, and never upgrade | Accepted |
| [0002](0002-synthetic-data-only.md) | Synthetic data only | Accepted |
| [0003](0003-firestore-project-one-free-database-as-shared.md) | Firestore (the project's one free database) as the shared state store | Accepted |
| [0004](0004-cloud-run-scale-zero-one-instance-cpu-only.md) | Cloud Run, scale to zero, one instance, CPU only during requests | Accepted |
| [0005](0005-github-actions-authenticates-google-cloud.md) | GitHub Actions authenticates to Google Cloud through Workload Identity Federation; no key exists | Accepted |
| [0006](0006-gemini-free-tier-through-e2a-managed-providers.md) | Gemini free tier through e2a-managed-providers, with deterministic fallbacks | Accepted |
| [0007](0007-model-never-moves-money-policy-checks-plus.md) | A model never moves money: policy checks plus a second person's approval | Accepted |
| [0008](0008-governance-is-policy-data-yaml-with-per.md) | Governance is policy data in YAML, with per-customer overrides laid over a base | Accepted |
| [0009](0009-grounded-answers-citations-must-be-records.md) | Grounded answers: citations must be records that were read, and stated figures must occur in them | Accepted |
| [0010](0010-intent-plain-request-is-read-by-rules-not.md) | The intent of a plain request is read by rules, not the model | Accepted |
| [0011](0011-lexical-bm25-search-over-customer-documents.md) | Lexical (BM25) search over the customer's documents, not embeddings | Accepted |
| [0012](0012-per-tenant-flight-share-per-instance.md) | Per-tenant in-flight share, per instance | Accepted |
| [0013](0013-other-services-serve-one-tenant-per-deployment.md) | The other services serve one tenant per deployment | Accepted (limitation) |
| [0014](0014-approvals-expire-lazily-with-compare-set.md) | Approvals expire lazily, with a compare-and-set, and answer HTTP 410 | Accepted |
| [0015](0015-close-reconciliation-exception-through.md) | Close the reconciliation exception through reconciliation's resolve route, which re-reads the ledger | Accepted |
| [0016](0016-correlation-id-every-call-one-json-log-line.md) | A correlation id on every call and one JSON log line per request | Accepted |
| [0017](0017-promote-with-canary-gate-automatic-rollback.md) | Promote with a canary, a gate and an automatic rollback; `ops deploy` bypasses it | Accepted |
| [0018](0018-terraform-for-infrastructure-observability.md) | Terraform for infrastructure; the observability stack is applied by hand | Accepted |
| [0019](0019-scenario-must-not-consume-finite-seeds.md) | The scenario must not consume finite seeds: alternate the payer account and restock daily | Accepted |
| [0020](0020-remove-pip-from-runtime-image.md) | Remove pip from the runtime image | Accepted |
| [0021](0021-5-second-database-connection-timeout.md) | A 5-second database connection timeout in settlement-service | Accepted |
| [0022](0022-log-based-metrics-from-one-json-line-per.md) | Log-based metrics from one JSON line per answer | Accepted |
| [0023](0023-platform-wide-engineering-records-live.md) | Platform-wide engineering records live in the assistant repository | Accepted |
