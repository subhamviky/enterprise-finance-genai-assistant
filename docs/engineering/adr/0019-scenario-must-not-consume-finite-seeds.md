# ADR 0019: The scenario must not consume finite seeds: alternate the payer account and restock daily

- **Status:** Accepted
- **Date:** 2026-11 (Phase B)
- **Deciders:** repository owner

## Context

The 150,000 EUR test payment drained a seeded ledger account after about six runs; orders drained seeded stock after about sixteen.

## Options considered

A) Seed more. B) Reset between runs. C) Alternate the payer account, and top stock up to par once per UTC day (`O2C_DAILY_RESTOCK`).

## Decision

C. The restock is keyed by day, so several starting instances add stock once.

## Consequences

The scenario is repeatable. The limit is visible: a same-day second restock adds nothing (post-incident review 0008). Where stock is real, restocking must be off.
