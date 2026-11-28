# ADR 0017: Promote with a canary, a gate and an automatic rollback; `ops deploy` bypasses it

- **Status:** Accepted
- **Date:** 2026-11 (Phase C)
- **Deciders:** repository owner

## Context

A deploy straight to 100% of traffic has no safety net.

## Options considered

A) Direct deploy. B) A no-traffic candidate on a tag URL, a 10% shift, the 14-step scenario as a gate, 100%, the gate again, rollback on failure.

## Decision

B in `.github/workflows/promote.yml`, reusing `landscape-gcp` as the gate; `ops deploy` stays for rebuilding. A `break` switch ships a deliberately broken candidate to demonstrate rollback. A rollback of a broken candidate also writes a clean no-traffic revision so the fault is not left in the service template.

## Consequences

Changes that matter are gated and reversible. The canary has almost no real traffic, so the gate, not live error rates, catches a bad candidate (gap G-13). Tokens minted for the service URL are accepted on the tag URL (verified on the first gated run).
