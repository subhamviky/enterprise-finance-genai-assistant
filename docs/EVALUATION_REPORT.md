# Evaluation report: genai-assistant-service

Source: `main` at `873bd7a`; E2A v1.11.0; the release gate `python -m genai_assistant_service.release.gate`. Date: 25 November 2026.

## What kind of evidence this is

| | |
|---|---|
| Evidence kind | **wiring** (the sets) and **live cloud** (the section Live cloud run). In the sets the model is E2A's simulated model, which answers with the rules in `services/simulated.py`; every check an agent applies to a model answer is the same one a real model faces |
| Profile and model | `simulated`; no model id |
| Systems of record | in-memory stand-ins that keep the real services' HTTP contracts and wording (`standins/landscape.py`) |
| Trials per case | 1 (the simulated model is deterministic) |
| What it proves | the wiring: routing, tool choice, the checks on answers and proposals, policy, approval, idempotency, fallbacks, redaction, tenant separation |
| What it does not prove | how well a real model answers, how fast the cloud is, how often a real model is refused or rate-limited. That evidence needs the `gemini_api` profile and the account (`docs/RUNBOOK.md`, Section 8) |

## Results

| Set | Cases | Passed |
|---|---|---|
| Golden | 53 | 53 |
| Red-team | 9 | 9 |
| **Total** | **62** | **62** |

Release gate stages: static security, scaffold compliance, evaluation (score 1.0), artifact compilation, dynamic security (the red-team set) and the deployment rollout stage passed; tests ran in the CI's own step (66 passed).

### Golden set by group

| Group | Cases | What each case checks |
|---|---|---|
| Investigate an unmatched line | 8 | the answer states the difference and cites the exception, the bank line and the settlement; the right tools were called; nothing was written |
| Explain a settlement | 12 | completed, flagged, failed and pending settlements are explained from the settlement, its events and its audit findings |
| Explain an order | 6 | a paid and a cancelled order, through their settlements |
| Propose | 8 | a small short payment becomes a proposal awaiting approval; a difference over the limit, a line with no candidate, and a failed settlement give no proposal; nothing is written |
| Approve and reject | 5 | a second person approves: one posting, read back; the requester and a wrong role are refused; a rejection posts nothing |
| Unsupported | 4 | no identifier: the help text and no tool call |
| Unknown identifiers | 3 | a line, a settlement and an order that do not exist: not found, nothing invented |
| Outages | 4 | the model down (investigation, proposal) and settlement-service down: degraded answers, no proposal, the gap stated |
| Tenants and roles | 3 | another tenant reads nothing; a role without entitlement is refused before any read |

### Red-team set

| Group | Cases | What each case checks |
|---|---|---|
| Prompt injection | 6 | five in the request (reveal the prompt, execute now, act as the approver, refund on instruction) and one inside a record: none causes a posting, none reveals a prompt |
| Personal data | 3 | a card number, an IBAN and an e-mail address in the request do not come back |

## Measures

Measured in-process on the stand-ins with the simulated model, one run of the 62 cases.

| Measure | Value | Note |
|---|---|---|
| Task success (cases passed) | 62 of 62 | |
| Tool calls per case | mean 3.0, maximum 7 | the maximum is an approval case: reads, the proposal's reads, the re-read, the post and the ledger read |
| Unauthorised actions | 0 | `post_adjustment` was called twice, in the two cases in which a second person approved; in no other case |
| Cases answered without a tool call | 13 | the 4 unsupported requests, the entitlement refusal, the 5 request injections and the 3 personal-data requests |
| Degraded answers | 14 | the no-proposal cases, the unknown identifiers, the model-down cases, the cross-tenant cases and the injection inside a record: each said so and stated the reason |
| Wall time per case | p50 13 ms, p95 24 ms, maximum 203 ms | in-process, no network, no real model: **not** a measure of the deployed service |
| Tokens and cost | not measured | the simulated model reports no real tokens; a live run records them |
| Error rate | 0 unexpected errors | |

## Beyond the sets

| Evidence | Result |
|---|---|
| Unit and integration tests | 66 passed: the journeys, the failure-injection matrix (13), safety (8), the HTTP API with Cloud Run identity (4), the converter of the placeholder files (6) |
| Firestore pass in CI | the suite again with approvals, claims and receipts in the Firestore emulator |
| The landscape scenario | 13 steps over the five real services on the emulators: an order, its event through Pub/Sub, an audit flag, a short payment, the cited explanation, a proposal, the investigator refused and a second person accepted, one posting to a balanced ledger, replays with no second posting and no second finding, an injection refused, another tenant reading nothing. It also ran against the five services in memory, with the assistant behind identity |
| Conformance | E2A strict conformance: no errors |

## Live cloud run (25 November 2026)

The same 13-step scenario, against the five services on Google Cloud Run in the trial project (region us-central1; Firestore, Pub/Sub, a PostgreSQL ledger on an e2-micro VM; the assistant on the Gemini free tier, `gemini-3.5-flash-lite`), run by the `landscape-gcp` workflow with target `cloud`: GitHub Actions authenticates to Google with a short-lived identity (no stored key), and every call carries a Google ID token that Cloud Run IAM checks. Result: **every step passed** (step 7a, the requester approving their own proposal, runs only in the local run, where one identity can claim both roles; the cloud run covers 7b and 7c).

| Step (cloud run) | Seconds | What dominated |
|---|---|---|
| 1 Two orders (3 printers, a varying number of scanners) paid through settlement | about 8 from the start of the scenario | two ledger writes through four services |
| 2, 3 Audit-ai receives the settlement events (Pub/Sub push) and flags the 150,000 EUR settlement | about 1 each | push delivery |
| 4 Statement: one line matched, one exception | about 1.4 | the lines cross Pub/Sub and are decided by reconciliation; the scenario waits for both |
| 5 The assistant explains the short payment (reads 10 to 15 records from four systems) | **79** | the free-tier model; the reads themselves took about 1 second in total (agent latency 0.85 s in the log) |
| 6 It proposes a 2.50 EUR write-off and waits | **24** | the model call |
| 7b, 7c, 8 Refusal, approval, one posting read back, balanced ledger | about 1 each | ledger and Firestore only; no model call |
| 9a, 9b Replays | 8 and 10 | 9b includes an 8-second wait for the redelivered event |
| 10a, 10b Injection refused, another tenant reads nothing | under 1 | no model call for the refusal |
| **Whole scenario** | **about 125** | |

Reading the table: every step that does not call the model finishes in about a second, including the approval and the ledger posting. The two steps that call the model took 79 and 24 seconds, so the live latency of an investigation is the free-tier model's, not the landscape's. In an earlier run the model answered 503 "high demand" and the client waited its full 60 seconds; each call is now bounded at 12 seconds with one retry (`LLM_SDK_TIMEOUT`, `LLM_SDK_MAX_RETRIES`), so a busy model degrades the answer to the verified facts instead of making the caller wait.

Cost: the billing report for 1 to 25 November 2026 shows **₹0.00** against ₹28,569.00 of trial credit (none consumed). The budget alert is set at ₹1, so the first charge would send an e-mail.

## Findings that changed the code

| Found by | Finding | Change |
|---|---|---|
| The scenario on the real services | reconciliation did not expose a bank line's amount | a read-only service route in reconciliation, and the `get_bank_line` tool |
| The scenario | settlement-service returns amounts as JSON numbers (`171.0`) | every amount is formatted alike; the stand-ins return numbers too |
| The scenario | the stand-ins' wording differed from the real services' | the stand-ins use the real wording; the difference to the nearest open item is computed from the two records |
| The first evaluation run | the card-number redaction pattern matched settlement identifiers | the pattern excludes identifiers joined by hyphens |
| The failure matrix | a model failure ended a request instead of falling back | the three model agents fall back on any model error |
| **The first cloud run** | a person's Google ID token names its issuer `accounts.google.com`, a service account's `https://accounts.google.com`; only the second was trusted, so people were refused | both spellings are trusted (`E2A_IDENTITY_TRUSTED_ISSUERS`); a test covers the person's form |
| The first cloud run | Gemini wraps JSON in a markdown code fence; the strict parser read it as invalid, and a model fallback ends the workflow, so a valid request answered "no record was found" | the three agents read a JSON object from a fence or a sentence; an unreadable intent reply is read with the rules and still investigates |
| The first cloud run | the model's free-text reason was part of the idempotency claim of an adjustment, so replaying a request made a second, postable proposal for the same write-off (the scenario's replay step caught it before anyone approved it) | the claim identifies what is proposed (person, line, action, settlement, amount, currency), not the wording |
| The first cloud run | the model cited only the two records it relied on, so a check that the answer cited the settlement and the audit finding failed although the answer was grounded | the response lists `records_read` (deterministic); the model's citations must be among them |
| The first cloud run | each model call waited 60 seconds before giving up when the free-tier model answered 503 | each call is bounded (12 seconds, one retry); the fallback answers with the verified facts |
| The first cloud run | the deployed O2C service was refused by Firestore when its access was conditioned on the shared database name | the condition applies only to a service's own database (O2C Terraform) |
| The first cloud run | a repeat run on the same landscape was refused as a duplicate of the first run's bank line, and an older run's open settlement of the same amount could be chosen as the closest item | each run uses its own orders, bank lines and amounts |

## Open

| Item | Needed to close it |
|---|---|
| Live-model evidence over the 62-case sets (answer quality, refusals, rate limits, tokens, cost per request) | run the gate with `E2A_PROVIDER_PROFILE=gemini_api` and `E2A_SWAP_LIVE=true`: about 190 model calls, inside the free daily limit of 500 but about 15 minutes at 15 requests per minute; not yet run |
| Deployed latency percentiles and cold start | the scenario gives one run (above); p50 and p95 need repeated runs |
| Several trials per case | needed once the model is not deterministic |
| Model availability | the free-tier model answered 503 at times; the answers then degrade to the verified facts and say so |
