# ADR 0016: A correlation id on every call and one JSON log line per request

- **Status:** Accepted
- **Date:** 2026-11 (Phase B)
- **Deciders:** repository owner

## Context

'Step N failed' across five services is slow to diagnose.

## Options considered

A) Cloud Trace first. B) A correlation id header carried on every call, one JSON line per request in each service, a script that counts the id in each service's log.

## Decision

B. `X-Correlation-Id` is kept or created at ingress and sent on every tool call; `landscape/trace_check.sh` verifies one run appears in all five.

## Consequences

Cheap, and it turned a diagnosis into minutes (post-incident reviews 0002 and 0003). Cloud Trace spans are not done (optional).
