# ADR 0013: The other services serve one tenant per deployment

- **Status:** Accepted (limitation)
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

Making reconciliation and the ledger multi-tenant is large and not needed to show the assistant's customer-shaping.

## Options considered

A) Make every service multi-tenant. B) Keep one tenant per deployment and test the assistant with two customers on stand-ins.

## Decision

B. The assistant is multi-tenant; reconciliation takes `RECON_TENANT`; ledger accounts are seeded for acme.

## Consequences

Isolation is proven on stand-ins, not on the live cloud for a second customer. Documented as gap G-10.
