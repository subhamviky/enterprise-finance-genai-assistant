# 0009: Cloud Shell could not push images or apply Terraform

- **Date of the work:** 2026-11 (the exact day was not recorded)
- **Severity:** SEV-4 (see README)
- **Status:** Actions complete
- **Authors:** repository owner, with Claude

## Summary

From Cloud Shell, `docker push` to Artifact Registry was refused (connection refused) and Terraform failed on an IPv6 address.

## Impact

None on users. Operator time lost and a worse operator experience from a phone.

## Timeline

- docker push fails intermittently.
- Terraform provider calls fail on IPv6.
- Mitigation: builds moved to Cloud Build blocks, then to a GitHub-runner `ops` workflow with a button; for Terraform in Cloud Shell, IPv6 is disabled with a sysctl before applying.

## Root cause

1. The operator environment's network is outside the project's control.
2. Deploy steps depended on it.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

Moving repeatable steps to a CI runner removed the dependency and made them runnable from a phone.

## Action items

| Action | Type | Status |
|---|---|---|
| `ops deploy` workflow | mitigate | Done (ADR 0017, 0018) |
| Document the IPv6 workaround | mitigate | Done (RUNBOOK) |
