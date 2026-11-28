# ADR 0022: Log-based metrics from one JSON line per answer

- **Status:** Accepted
- **Date:** 2026-11 (Phase B leftover)
- **Deciders:** repository owner

## Context

The model's share of the work (degraded answers) and the token cost were not visible without reading logs.

## Options considered

A) Custom metrics API calls from the service. B) Log-based metrics created by Terraform from a structured line.

## Decision

B. The assistant logs `assistant_answer` (status, intent, degraded, intent_by, tokens; no question and no user); `landscape/observability` defines `assistant_answers` and `assistant_tokens`.

## Consequences

No new code path that can fail a request, and no charge within Cloud Logging's free allocation. Metrics only count lines logged after they exist.
