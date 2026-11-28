# ADR 0008: Governance is policy data in YAML, with per-customer overrides laid over a base

- **Status:** Accepted
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

Customers differ in currencies, limits, roles, number of approvers, decision window and masking. Hard-coding each in code would fork the service.

## Options considered

A) A code branch per customer. B) A policy file per customer that overrides the base for its tenant's requests.

## Decision

B. `policies/governance.yaml` is the base; `policies/customers/<tenant>.yaml` names only what differs; `PolicyBook.for_tenant` resolves it; requests run inside `governing(tenant)` so the framework's stages use the customer's policy.

## Consequences

A customer is data, tested with the same service (tests/test_customers.py). The framework's conformance rules forced the use of a context manager rather than overriding public methods. Limit: the other services serve one tenant per deployment (ADR 0013).
