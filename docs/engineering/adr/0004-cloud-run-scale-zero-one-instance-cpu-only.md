# ADR 0004: Cloud Run, scale to zero, one instance, CPU only during requests

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

Compute must stay in the free tier and cost nothing when idle.

## Options considered

A) A VM per service. B) GKE Autopilot. C) Cloud Run with minimum 0 and maximum 1 instance.

## Decision

C, 512 MiB, never public, CPU allocated only during requests.

## Consequences

Idle cost is zero and deployments are revisions with traffic splitting (ADR 0017). The costs are cold starts (the first request after idle is slow) and that capacity limits, such as the per-tenant in-flight share (ADR 0012), are per instance.
