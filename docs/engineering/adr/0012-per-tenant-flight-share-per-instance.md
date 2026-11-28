# ADR 0012: Per-tenant in-flight share, per instance

- **Status:** Accepted
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

One noisy customer must not fill the service's capacity and starve a quiet one.

## Options considered

A) A global limit only. B) A per-tenant cap per instance. C) A shared limiter across instances.

## Decision

B. `max_inflight_per_tenant` (4 of 8); a tenant over its share is refused with a retryable 503 while others are served.

## Consequences

Simple and testable with an async gate. With several instances a tenant could hold more slots in total (gap G-11); at one instance on the free tier this does not occur.
