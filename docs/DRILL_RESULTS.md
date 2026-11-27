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

## Drill 2: Pub/Sub delivery to audit-ai paused

Not yet recorded.

## Drill 3: restore of the ledger backup

Ran to its end (the scratch database was dropped). Counts and timing not yet recorded.
