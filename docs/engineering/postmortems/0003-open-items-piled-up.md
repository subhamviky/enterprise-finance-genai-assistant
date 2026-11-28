# 0003: Open items piled up; reconciliation stopped seeing the current settlement

- **Date of the work:** 2026-11-27
- **Severity:** SEV-2 (see README)
- **Status:** Actions partly open
- **Authors:** repository owner, with Claude

## Summary

A defect I introduced in Phase A: closing an exception after an approved write-off never consumed the settlement's open item. Open items accumulated per account, and reconciliation, which compares a bank line with the oldest items, stopped finding the current run's settlement. It surfaced as the model 'failing' at the proposal step.

## Impact

In a real deployment this would have left exceptions open or matched to the wrong settlement: a customer-visible wrong outcome. In the demonstration, the assistant refused to propose and the scenario failed.

## Timeline

- Phase A: the assistant asks reconciliation to resolve the exception after a posted write-off; reconciliation closes it if the ledger holds the adjustment.
- Phase B: runs begin to fail at the proposal step; the model appears to choose or refuse wrongly.
- The correlation id and the reconciliation log show the line's candidates are old settlements, not the current run's.
- Root cause: `resolve` closed the exception but left the settlement's open item OPEN, so the account's oldest-first list kept growing.
- Fix: resolution consumes the open item (`_consume_open_item`); a one-off cleanup (`close_stale_open_items.py`, an ops action) closed the existing stale items; a regression test fails without the fix.

## Root cause

1. The Phase A change satisfied its own test (the exception closed) but not the system property (open items reflect what is still unpaid).
2. The matcher's 'oldest first' behaviour made the symptom appear only after enough runs.
3. The symptom was in a different service and looked like model behaviour.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

The correlation id made it a few minutes of reading logs instead of a hunt. The refusal of a mismatching proposal held: nothing wrong was posted.

## Action items

| Action | Type | Status |
|---|---|---|
| Consume the open item on resolution | prevent | Done (payment-reconciliation-engine) |
| Regression test that fails without the fix | prevent | Done |
| Ops action to close stale open items (dry run by default) | mitigate | Done |
| A scenario check that the exception's open item is gone | detect | Open (considered) |
