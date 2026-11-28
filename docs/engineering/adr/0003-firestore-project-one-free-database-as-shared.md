# ADR 0003: Firestore (the project's one free database) as the shared state store

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

The assistant, reconciliation and O2C need shared, transactional state (approvals, idempotency claims, open items, stock) that survives restarts and redeploys. Cloud SQL has no free tier; one Firestore database in the project is free.

## Options considered

A) Cloud SQL. B) Memorystore. C) Firestore through E2A's `BaseTransactionalStore` adapter. D) Per-service files or memory.

## Decision

C. State sits behind E2A's store ports; Firestore is the production backend and an in-memory store is used in tests; CI runs a second pass against the Firestore emulator. Each service uses its own collection prefix in the one database.

## Consequences

A redeploy mid-approval loses nothing (drill 4). Compare-and-set is the concurrency primitive, and every store that needs a counter or state change uses it. The settlement ledger is the exception: it is PostgreSQL on an Always Free VM because it needs relational constraints and a balanced ledger (see the settlement repository's ADRs).
