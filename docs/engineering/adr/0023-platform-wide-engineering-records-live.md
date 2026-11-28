# ADR 0023: Platform-wide engineering records live in the assistant repository

- **Status:** Accepted
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

Five repositories share one deployment, one pipeline set (`landscape-gcp`, `ops`, `promote`), one observability stack and one teardown. Copies would drift.

## Options considered

A) The same documents in every repository. B) Platform documents once in the assistant repository (it owns the workflows), service-specific ones in each repository with links.

## Decision

B. Cost and capacity, disaster recovery, teardown, SLO policy, incident response and release process are here; each other repository has the parts that are about its service and links back.

## Consequences

One place to maintain; a reader of another repository must follow a link for platform facts.
