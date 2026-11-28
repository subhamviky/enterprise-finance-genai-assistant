# Cost and capacity

- **Status:** Draft 2026-11-28, awaiting owner review · **Platform document.** The landscape costs nothing by design and is never upgraded (ADR 0001). This records what the limits are, what breaks first, and what a paid sizing would have to answer; it contains no price quotations because those change.

## Where the cost is zero, and why

| Resource | Shape | Why it is free |
|---|---|---|
| Cloud Run (5 services) | minimum 0, maximum 1 instance, CPU only during requests, 512 MiB, never public | within the Always Free request, CPU and memory allowances at this traffic |
| Firestore | one database in the project, collections per service | the one free database per project |
| Ledger VM | one e2-micro in an eligible region, no external address | Always Free e2-micro |
| Artifact Registry | one repository with a cleanup policy keeping it within 0.5 GB | free storage allowance |
| Cloud Scheduler | exactly three jobs for the account (settlement maintenance, reconciliation run, O2C combined job) | three free jobs |
| Pub/Sub | settlement events and a dead-letter topic | within the free throughput |
| Cloud Monitoring SLOs, log-based metrics | SLOs have no price; metrics sit in Cloud Logging's free allocation at this volume | |
| Gemini API | free tier through an AI Studio key | quota-limited, not charged |
| Billing guard | a budget alert at the first cent (₹1 in the trial's billing currency); Terraform refuses non-free regions and models | |

## Model limits (from the owner's AI Studio table, 26 November 2026)

| Model | RPM | TPM | RPD | Use |
|---|---|---|---|---|
| Gemini 3.5 Flash Lite | 15 | 250K | 500 | the model in use |
| Gemini 3.1 Flash Lite | 15 | 250K | 500 | like-for-like comparison |
| Gemma 4 26B / 31B (open-weight) | 30 | 16K | 14,400 | bulk and adversarial runs; the 16K a minute is the binding limit |
| other Gemini models | 5 to 10 | 250K | 20 | spot checks only |

A multi-trial run of the six scenarios (5 trials) is about 50 model requests; `measure.py --compare --runs 3` is 54. Only one model family's run per day is advisable.

## What breaks first (capacity)

1. **The model's daily and per-minute quota** (500 requests a day for the Flash Lite models): live evaluation is paced and spread across days; the service degrades to facts when a call fails.
2. **Cold starts**: the first request after idle waits for an instance (and, for settlement, a database connection within 5 s).
3. **One instance, per-tenant share of 4 of 8 in flight**: a sixth concurrent request is refused with a retryable 503.
4. **Seeded stock and ledger balances** drain with scenario runs (alternating payer; daily restock).
5. **The e2-micro** (1 GB memory) bounds the ledger's database size and concurrent connections.
6. **Firestore free quota** (reads, writes, storage per day) would be hit first by a load test; none has been run.

No load test has been run; capacity numbers above are limits and observations, not measurements under load.

## What a paid, real-customer sizing would have to answer

Requests per day and peak concurrency per customer; tokens per request (the log-based metric gives this once traffic exists, and the simulated measurement shows one fewer model call per plain request); the price of the chosen model per million tokens at that volume; Firestore operations per request; the ledger's instance class, HA and backup retention; networking and logging volumes; support and compliance costs. A request costs, in model terms, one to three calls and a few hundred to a few thousand tokens (measured offline; live figures in `docs/EVALUATION_REPORT.md`).

## Cost controls in force

Budget alert at the first cent; free-tier-only Terraform guards; the Billing report is checked after each phase; the trial is never upgraded; the whole landscape is destroyed in the week of 8 February 2027 ([teardown](teardown-and-exit.md)).
