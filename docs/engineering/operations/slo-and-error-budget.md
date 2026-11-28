# Service level objectives and error-budget policy

- **Status:** Reviewed 2026-11-28 · **Owner:** repository owner · **Implemented in:** `landscape/observability` (Terraform, tested with a mocked provider) · **Platform document**: applies to all five services.

## Objectives

| Service | SLI | Objective | Window |
|---|---|---|---|
| each of the five (assistant, settlement, reconciliation, audit-ai, O2C) | availability: requests not answered with a server error (5xx), from Cloud Run's request count | **99%** | 28 days, rolling |
| settlement-service, reconciliation-service | latency: requests answered within 1 s, from Cloud Run's request latencies | **95%** | 28 days, rolling |
| genai-assistant-service, audit-ai-service, O2C | **no latency objective**: a language model is in the path and its latency is not ours to promise | n/a | |

The assistant's model use is watched with a different signal: the **degraded-answer rate** (`assistant_answers` with `degraded=true`) and tokens per request (`assistant_tokens`), which are indicators, not objectives (no target until there is traffic to set one against).

## Alerts

A fast-burn alert on every SLO: the error budget burning ten times too fast over one hour (`select_slo_burn_rate(..., "1h") > 10`). No notification channel is configured by default (nothing is sent; alerts show in the console); pass `notification_channels` to the stack to send them. The alerting charge in Google's table starts on 1 September 2027, after this landscape is gone.

## Error-budget policy

| Budget remaining | What we do |
|---|---|
| more than 50% | normal work; changes go through `promote` |
| 25% to 50% | no new risky changes; read the cause of the spend (the correlation id, `trace_check.sh`); fix reliability defects before features |
| under 25% | freeze feature changes to the affected service; only fixes, rollbacks and reliability work ship; write a [post-incident review](../postmortems/README.md) if a single event spent more than 10% |
| exhausted | rollback to the last revision that met the objective; the freeze stays until the rolling window recovers or the owner records an explicit exception |

Deliberate failure drills spend budget by design. They are recorded in `docs/DRILL_RESULTS.md` and do not trigger the policy, but they are named in the evidence so the spend is explained (on 27 November 2026 the ledger-outage drill left settlement-service at 40.7% of its availability budget and 60.5% of its latency budget).

## Limits of these numbers

Traffic is a scenario run's few dozen requests, so a single failure moves a percentage by a lot. The objectives demonstrate the mechanism, not a service's true reliability. With real traffic the targets, windows and burn-rate thresholds must be re-derived from user journeys.

## Review

Quarterly in a real team; here, before the Phase D evidence capture and again at teardown.
