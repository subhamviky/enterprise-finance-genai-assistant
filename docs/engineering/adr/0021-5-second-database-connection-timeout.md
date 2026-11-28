# ADR 0021: A 5-second database connection timeout in settlement-service

- **Status:** Accepted
- **Date:** 2026-11 (Phase B)
- **Deciders:** repository owner

## Context

With the ledger VM stopped, requests waited 30 s for a connection instead of failing fast, so health probes saw no answer.

## Options considered

A) Keep 30 s. B) Shorten the pool's connection timeout to 5 s so failures are typed and quick.

## Decision

B (`application-gcp.yml`, tested by `GcpPoolSettingsTests`); drill 1 is to be repeated to measure the effect.

## Consequences

Callers get a fast 5xx they can handle. A short database stall now fails requests that 30 s would have survived; acceptable for this workload.
