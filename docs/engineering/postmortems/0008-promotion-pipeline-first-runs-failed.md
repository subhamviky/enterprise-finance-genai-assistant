# 0008: The promotion pipeline's first runs failed

- **Date of the work:** 2026-11-28
- **Severity:** SEV-4 (see README)
- **Status:** Actions partly open
- **Authors:** repository owner, with Claude

## Summary

The first runs of `promote` failed at the traffic shift (an output read from the wrong step left the previous revision unknown), and after the fix the gate failed at step 1 because the O2C stock was spent, and a same-day restock cannot add stock.

## Impact

None on users. The service kept serving the previous revision at 100% the whole time; two no-traffic candidate revisions and a tag were left behind.

## Timeline

- 04:52 UTC: run 1: `shift10` fails with `Invalid flag value [=90]` (empty previous revision).
- 04:54 UTC: run 2: the same.
- Cause: the job output `prev` read `steps.rev.outputs.prev`, but `prev` is set by the step `prev`. Fix pushed and merged.
- 05:00 UTC: run 3: the canary shifted, the gate ran against the tag URL and failed at step 1 (O2C 'insufficient stock'); `rollback` ran and restored the previous revision. The tag-URL token audience, the part flagged as unverified, worked.
- 07:19 UTC: run 4: the same stock failure after a restock: stock tops up once per UTC day and had already been topped up that day.
- Resolution: wait for the next UTC day (05:30 IST), restock, rerun.

## Root cause

1. The workflow could not be run locally; YAML lint cannot catch a wrong step reference.
2. I gave a restock command without checking the once-per-day key.
3. Finite resource again (0001, 0002).

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

The rollback executed correctly on a real failure; the gate reached the candidate through the tag URL.

## Action items

| Action | Type | Status |
|---|---|---|
| Fix the output reference | prevent | Done |
| Consider a restock input on the ops workflow, or a stock precheck in the gate | prevent | Open (considered) |
| Record the once-per-UTC-day rule next to the restock command | prevent | Done (RUNBOOK) |
