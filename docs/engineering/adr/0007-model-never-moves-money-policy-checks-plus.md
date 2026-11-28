# ADR 0007: A model never moves money: policy checks plus a second person's approval

- **Status:** Accepted
- **Date:** 2026-11 (GCP-01)
- **Deciders:** repository owner

## Context

The assistant drafts write-offs and refunds. A language model can be wrong or manipulated.

## Options considered

A) Let the model post within limits. B) The model proposes; code validates; one person approves. C) As B, with the approver never the requester (four eyes).

## Decision

C. A proposal is checked by `Policy.check_proposal` (limits, currency, settlement in evidence and COMPLETED, amount equals the exact gap, not ambiguous); nothing is written before approval; the approver must hold the approver role and differ from the requester; the post is idempotent and read back.

## Consequences

The dangerous action is guarded by deterministic code and a human, not by prompt wording. Costs: friction (a second person), and a refusal rate when the model drafts something the policy rejects (visible as `fallback` in trials).
