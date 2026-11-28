# Disaster recovery plan

- **Status:** Reviewed 2026-11-28 · **Platform document.** Targets are those the drills measured, not promises: a single-region, single-author demonstration.

## What can be lost, and what protects it

| Component | Failure | Protection | Measured |
|---|---|---|---|
| Ledger (PostgreSQL on an e2-micro VM) | VM stopped or crashed | systemd restarts the container; the data is on the persistent disk; the password is read from Secret Manager at boot | **recovery 40 s** from the start request to healthy (drill 1) |
| Ledger | disk or database loss | a daily `pg_dump` to a Cloud Storage bucket; the VM can create backup objects but not read or delete them | **restore of 54 settlements, equal to live, in 31 s** into a scratch database (drill 3) |
| Event delivery to audit-ai | push paused or failing | Pub/Sub keeps events 24 hours; a dead-letter topic after 5 attempts; the audit claim is keyed on the event id, so a redelivery is a no-op | first delivery **10 s** after restore; the backlog drained within the next minute (drill 2) |
| Assistant state (approvals, claims) | service restart or redeploy | state is in Firestore, not the service | an approval survived a redeploy and posted once (drill 4) |
| Any Cloud Run service | bad revision | traffic split and rollback to the previous revision | automatic rollback on a failed gate (Drill 6) |
| Firestore | regional outage, deletion | **none beyond Google's own durability**: no export is scheduled | not tested |
| The whole project | deletion or trial expiry | Terraform stacks, scripts and documents are in git; state and data are not | rebuild is timed in Phase D |

## Objectives

| | Target | Basis |
|---|---|---|
| RTO (ledger VM stop) | 2 minutes | drill 1 (110 s whole outage) |
| RTO (rebuild of the whole landscape from git) | to be measured in Phase D (destroy and rebuild, timed) | |
| RPO (ledger) | up to 24 hours | daily backup; anything since the last dump is lost on a disk loss |
| RPO (approvals, claims) | zero within Firestore's guarantees | state is written before the response |

## Procedures

1. **Ledger VM down:** `gcloud compute instances start ledger-db --zone us-central1-a`; wait for `/actuator/health` 200.
2. **Ledger data lost:** follow Drill 3 (download the latest dump in Cloud Shell, `gunzip -t`, restore into a scratch database, compare counts, then restore into `settlement` deliberately, stopping settlement-service first).
3. **Audit feed broken:** restore the push endpoint, service account and audience of `audit-settlement-events`; check the dead-letter subscription.
4. **Bad revision:** roll back traffic (see the [release process](release-process.md)).
5. **Project lost:** re-apply the stacks in the order of RUNBOOK section 6, re-seed, rerun the scenario.

## Gaps

No scheduled Firestore export; backups live in the same project as the data they protect; restoring over the live database is described, not drilled; no multi-region design. These are acceptable for synthetic data on a free tier and would not be for real money.

## Testing the plan

The four drills are the tests (`docs/DRILLS.md`, `docs/DRILL_RESULTS.md`). Repeat drill 1 after the 5 s database connection timeout to measure its effect, and time a full rebuild in Phase D.
