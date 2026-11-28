# 0007: First backup restore failed

- **Date of the work:** 2026-11-27
- **Severity:** SEV-4 (see README)
- **Status:** Actions complete
- **Authors:** repository owner, with Claude

## Summary

Drill 3 first ran the restore from the database VM and failed with `gzip: unexpected end of file` and an empty scratch database.

## Impact

None. A drill, not an incident. It proved the backup path is least-privilege by accident.

## Timeline

- Restore script run on the VM.
- Download got a 403 hidden by `curl -sf`; `gunzip` was handed nothing.
- Cause: the VM's account has `roles/storage.objectCreator` only, on purpose: a compromised database host cannot read or delete its own backups.
- Drill redone from Cloud Shell as an operator would: download, `gunzip -t`, stream into the VM over IAP. Restored 54 settlements equal to the live 54 in 31 s.

## Root cause

1. The drill assumed the host could read what it wrote.
2. Silent flags hid a permission error.

## Detection

Found by running the scenario, a drill or a test; see the timeline for what made it diagnosable.

## What went well

A drill that fails for a reason of its own design is still evidence: it proved the write-only backup account.

## Action items

| Action | Type | Status |
|---|---|---|
| Restore drill runs as an operator, never from the host | prevent | Done (DRILLS.md) |
| Fail loudly on download errors | detect | Done |
