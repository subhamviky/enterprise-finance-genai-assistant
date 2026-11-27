# Failure drill results (GCP-02 Phase B)

Run in Cloud Shell on the real free-tier project, 27 November 2026. The drills and their commands are in `DRILLS.md`.

## Drill 1: the ledger database VM stops

| Measured | Result |
|---|---|
| `/actuator/health` before | 200 |
| `/actuator/health` with the VM stopped (45 s after the stop) | `000`: no answer within the probe's 10 s limit |
| Time to stop the VM, then to get the start accepted | 70 s |
| **Recovery: from the start request to health 200 again** | **40 s, with no manual repair** |
| Whole outage, stop to healthy | about 110 s |
| Scenario while the ledger was down (`landscape-gcp`, step 1) | failed, as it should: the orders could not be paid |
| What the log shows | `Connect timed out` to the database, `HikariPool-1 - Connection is not available, request timed out after 30000ms`, the health check failing on the database, then `UP` |

What this shows: settlement-service does not invent a result when its database is gone; payments fail, and nothing is half-written. After the VM starts, the database container, the password fetch from Secret Manager and the Cloud Run readiness probe bring everything back by themselves within a minute.

**An improvement it points at.** While the database was down, a request did not fail fast: it waited for the connection pool's 30-second timeout, so the health probe saw no answer at all (`000`) instead of a quick 503. For callers (the assistant, reconciliation) a quick, typed failure is easier to handle than a 30-second hang. The pool's `connectionTimeout` is the setting to shorten (for example to 5 s); the 30 s was never chosen for this case. Not changed yet: it needs a decision, since a shorter timeout also makes a slow start fail sooner.

### What happened after drill 1: a different failure, found because of it

The scenario failed again after the ledger had recovered. The correlation id (item 3 of this phase) made it diagnosable in minutes: settlement-service showed no errors after the outage, and O2C had answered 200 but refused both orders (`REFUSED`, no settlement id). Cause: O2C's seeded stock (50 printers, 200 scanners) was used up. Each scenario run buys goods and never returns them, and about 16 runs had been made that day. Not an effect of the drill, and not the circuit breaker first suspected. Fixed by a daily par-level top-up (`O2C_DAILY_RESTOCK`, off by default); `landscape-gcp` passes again with it on.

Two lessons recorded: (1) a test that consumes finite seeded resources (the ledger account earlier, the stock now) will eventually fail for reasons unrelated to the code under test, so such a scenario needs a restock or a reset by design; (2) the run's correlation id turned "step 1 failed" into a diagnosis without logging in to any service.

## Drill 2: Pub/Sub delivery to audit-ai paused

Run on 27 November 2026. The subscription `audit-settlement-events` was switched to pull-only (its push endpoint removed), the scenario was run while it was paused, then the push settings (endpoint, service account, audience) were restored and the scenario run again.

| Measured | Result |
|---|---|
| Scenario while delivery was paused (run at 14:54 UTC, `scenario-03ed0c`) | **failed at step 2**: `timed out waiting for audit-ai's finding for the scanners' settlement`. Step 1 (the orders are paid) passed: settlement-service was not affected. |
| What that proves | delivery had really stopped: the events were published and waiting in the subscription, and the audit service saw none of them |
| Scenario after the restore (run at 15:00 UTC, `scenario-d2fc46`) | **passed all 14 steps**, including 9b: a redelivered settlement event adds no second finding |
| Window | the paused run ended at about 14:56; the passing run started at 15:00, so delivery was restored within that interval |
| Time from the restore to the first delivered push | not captured in this run (to be added from the Cloud Shell output) |
| Repair needed | none: restoring the three push settings was the whole recovery |

What this shows: the audit service has no state of its own that an interruption of the feed can corrupt. Events wait in Pub/Sub (kept 24 hours), and when delivery resumes they are audited once; the claim keyed on the event id means a redelivery is a no-op. The cost of an outage of the feed is delay, not loss.

## Drill 3: restore of the ledger backup

Run in Cloud Shell on 27 November 2026, restoring into a scratch database and never touching the live one.

| Measured | Result |
|---|---|
| Backup restored | `settlement-20261127T122429Z.sql.gz`, 23,834 bytes (taken by the VM's daily timer, plus one started by hand) |
| Integrity (`gunzip -t`) | a whole, valid gzip |
| Settlements, live database | 54 |
| **Settlements, restored database** | **54** (equal) |
| Time for the restore | 31 s in total (four IAP connections, a 24 KB dump) |
| Cleanup | the scratch database was dropped; the live one was not touched |

**What the first attempt taught.** The drill first ran the restore from the database VM and failed: `gzip: unexpected end of file`, then an empty scratch database. The VM's service account can create objects in the backup bucket but cannot read them (`roles/storage.objectCreator`, on purpose: a compromised database host cannot read or delete its own backups). The download got a 403 that `curl -sf` hid, and `gunzip` received nothing. So the failed attempt proved the write-only backup account, and the drill was corrected to restore the way an operator would: download from Cloud Shell, check the file, stream it into the VM.

What this shows: the backup is not just present, it restores to the same row count; and the backup path is least-privilege, so restoring is a deliberate act by a person with access, not something the database host can do on its own.
