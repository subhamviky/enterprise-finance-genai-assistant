# 0001: A seeded ledger account drained by the test payment

- **Date of the work:** 2026-11 (the exact day was not recorded)
- **Severity:** SEV-3 (see README)
- **Status:** Actions complete
- **Authors:** repository owner, with Claude

## Summary

The scenario's 150,000 EUR payment between two seeded ledger accounts failed after about six runs because the paying account no longer had the balance.

## Impact

None on users. The cloud scenario failed at the payment step for a reason unrelated to the code under test, and each failure cost a diagnosis.

## Timeline

- Phase A: scenario runs on the real cloud pass repeatedly.
- After about six runs: the payment step fails with an insufficient-balance outcome from the ledger.
- Diagnosis: the ledger balance of the payer account, not any service fault.
- Fix: the payer alternates between two seeded accounts so each run's debit is another run's credit; the balanced-ledger step (step 8) still checks the books.

## Root cause

1. The scenario moved a large fixed amount in one direction on every run.
2. The seed gave the payer a finite balance.
3. Nothing in the scenario treated its own consumption of seeded resources as a design concern.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

The failing step named the payment, which pointed at the ledger quickly. Step 8 (a balanced ledger) caught nothing wrong, as it should.

## Action items

| Action | Type | Status |
|---|---|---|
| Alternate the payer account between runs | prevent | Done (landscape/scenario.py) |
| Record the rule: a scenario that consumes finite seeds needs a restock or a reset by design | prevent | Done (ADR 0019, RUNBOOK) |
| Print the failing step's reason, not only its name | detect | Done |
