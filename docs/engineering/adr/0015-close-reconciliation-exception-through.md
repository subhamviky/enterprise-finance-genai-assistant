# ADR 0015: Close the reconciliation exception through reconciliation's resolve route, which re-reads the ledger

- **Status:** Accepted
- **Date:** 2026-11 (Phase A)
- **Deciders:** repository owner

## Context

After an approved write-off posted, the exception stayed open: the assistant posted to the ledger directly.

## Options considered

A) The assistant marks the exception closed. B) The assistant asks reconciliation to resolve it, and reconciliation closes it only if the ledger holds an adjustment whose reference names the bank line.

## Decision

B. `POST /service/v1/exceptions/{line_id}/resolve` (role `reconciliation.resolve`). If reconciliation is down or refuses, the posting stands, the exception stays open and the receipt says so.

## Consequences

No system believes another's claim; the lifecycle closes with evidence. Reconciliation also consumes the settlement's open item (a defect fixed after this, post-incident review 0003).
