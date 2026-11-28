# ADR 0009: Grounded answers: citations must be records that were read, and stated figures must occur in them

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

A finance explanation that invents a settlement id or an amount is worse than none.

## Options considered

A) Trust the model's JSON. B) Require citations to be evidence ids and every id, amount and status word in the answer to occur in the evidence the model saw; otherwise use the deterministic fallback.

## Decision

B. The investigator agent returns confidence 0.0 for an ungrounded answer, so the fallback states the verified facts with their identifiers.

## Consequences

Hallucinated figures are not shown. A correct paraphrase that introduces a number not in the evidence is also refused (accepted trade-off). The same rule covers answers built from documents (ADR 0011).
