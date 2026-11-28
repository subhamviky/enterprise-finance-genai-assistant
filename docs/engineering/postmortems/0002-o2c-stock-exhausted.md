# 0002: O2C stock exhausted, scenario step 1 failing

- **Date of the work:** 2026-11-27
- **Severity:** SEV-3 (see README)
- **Status:** Actions complete
- **Authors:** repository owner, with Claude

## Summary

After about sixteen runs the scenario's orders were refused ('insufficient stock') because the seeded printers (50) and scanners (200) were used up. It appeared right after drill 1 and was first suspected to be an effect of the ledger outage.

## Impact

None on users. A passing scenario failed at step 1 on the day of the failure drills, which made it look like a consequence of the drill.

## Timeline

- Drill 1 stops and restarts the ledger VM; recovery takes 40 s.
- The scenario is run again to confirm nothing was lost and fails at step 1.
- The correlation id (Phase B item 3) shows settlement-service with no errors after the outage and O2C answering 200 with both orders REFUSED and no settlement id.
- Cause found in minutes: O2C's seeded stock was used up. Each run buys goods and never returns them.
- Fix: `O2C_DAILY_RESTOCK` tops each SKU up to its catalog level once per UTC day, keyed by the day so several instances add stock once.

## Root cause

1. Each run buys 3 printers and 2 to 21 scanners, with no returns.
2. Stock was seeded once, with create-if-absent, so a restart never reset it.
3. The same class of fault as 0001, repeated, because the lesson was not yet a rule.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

A single query on the run's correlation id turned 'step 1 failed' into a diagnosis without logging in to any service.

## Action items

| Action | Type | Status |
|---|---|---|
| Daily par-level restock, off unless `O2C_DAILY_RESTOCK=true` | prevent | Done (order-to-cash-agentic-ai) |
| Print the order status and reason in step 1 | detect | Done |
| State the rule in the drills and runbook | prevent | Done |
