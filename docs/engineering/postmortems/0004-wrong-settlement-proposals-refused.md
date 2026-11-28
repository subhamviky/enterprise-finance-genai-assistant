# 0004: A correct refusal of a wrong-settlement proposal, three times

- **Date of the work:** 2026-11 (the exact day was not recorded)
- **Severity:** SEV-4 (see README)
- **Status:** Actions complete
- **Authors:** repository owner, with Claude

## Summary

The assistant refused write-offs on the wrong settlement three times in three ways: a model that chose another settlement with the same amount; two equally good candidates; and a settlement reconciliation had never offered. Each refusal was correct; each real defect was upstream.

## Impact

None. The scenario failed at the proposal step until the causes were fixed. No wrong posting occurred.

## Timeline

- Run 1: the live model chose a different COMPLETED candidate that passed every other check; fix: the policy requires the settlement to be a candidate for the line and the amount to equal the exact gap.
- Run 2: two candidates fit equally because the scenario repeats amounts across runs; fix: the assistant refuses to guess, asks for the settlement to be named, and honours a named one; the prompt names the settlement a request names.
- Run 3: a settlement my own change had left unavailable to reconciliation (see 0003); fix there.

## Root cause

1. The prompt did not tell the model which settlement the request named.
2. Synthetic data repeated amounts, making ambiguity real.
3. A policy check cannot repair upstream data.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

The safety checks worked every time; the failures were informative rather than silent.

## Action items

| Action | Type | Status |
|---|---|---|
| Policy: settlement must be a reconciliation candidate and amount the exact gap | prevent | Done |
| Ambiguity is refused and the named settlement is honoured | prevent | Done |
| Prompt names the settlement | prevent | Done |
