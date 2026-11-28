# ADR 0014: Approvals expire lazily, with a compare-and-set, and answer HTTP 410

- **Status:** Accepted
- **Date:** 2026-11 (Phase B)
- **Deciders:** repository owner

## Context

An approval nobody decides must not stay postable forever.

## Options considered

A) A background sweeper. B) Check on read and on decision, record EXPIRED by compare-and-set.

## Decision

B. `ApprovalStore._expire_if_due`; the window is per customer; a late approval returns 410 and nothing is posted; a clock is injectable for tests.

## Consequences

No scheduler to run on a scale-to-zero platform. An expired approval shows as pending until it is read; the first read or decision records it.
