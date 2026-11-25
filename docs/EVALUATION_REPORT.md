# Evaluation report: genai-assistant-service

Source: `main` at `873bd7a`; E2A v1.11.0; the release gate `python -m genai_assistant_service.release.gate`. Date: 25 November 2026.

## What kind of evidence this is

| | |
|---|---|
| Evidence kind | **wiring**: the model is E2A's simulated model, which answers with the rules in `services/simulated.py`; every check an agent applies to a model answer is the same one a real model faces |
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

## Findings that changed the code

| Found by | Finding | Change |
|---|---|---|
| The scenario on the real services | reconciliation did not expose a bank line's amount | a read-only service route in reconciliation, and the `get_bank_line` tool |
| The scenario | settlement-service returns amounts as JSON numbers (`171.0`) | every amount is formatted alike; the stand-ins return numbers too |
| The scenario | the stand-ins' wording differed from the real services' | the stand-ins use the real wording; the difference to the nearest open item is computed from the two records |
| The first evaluation run | the card-number redaction pattern matched settlement identifiers | the pattern excludes identifiers joined by hyphens |
| The failure matrix | a model failure ended a request instead of falling back | the three model agents fall back on any model error |

## Open

| Item | Needed to close it |
|---|---|
| Live-model evidence (answer quality, refusals, rate limits, tokens, cost per request) | run the gate with `E2A_PROVIDER_PROFILE=gemini_api` and `E2A_SWAP_LIVE=true` after the cutover |
| Deployed latency and cold start | measure on Cloud Run |
| Several trials per case | needed once the model is not deterministic |
