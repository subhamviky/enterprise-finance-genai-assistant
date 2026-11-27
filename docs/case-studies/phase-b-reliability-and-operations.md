# Case study: making the landscape operable (GCP-02 Phase B)

*Simulated customer, real cloud: five services on the free tier of Google Cloud, a GenAI assistant that investigates bank-line exceptions and proposes write-offs that a second person approves. Dates are 26 and 27 November 2026. Every number below is from a run named in `DRILL_RESULTS.md`, `EVIDENCE.md` or `EVALUATION_REPORT.md`.*

## Situation

By the end of Phase A the landscape ran end to end on the real cloud: an order, its settlement event, an audit flag, a short bank payment, an assistant that explained it with citations and proposed a write-off, a second person's approval, one posting to a balanced ledger, and a closed reconciliation exception. A passing scenario shows that it *can* work. Phase B asked the operational questions: when something breaks, can we see where, does it recover by itself, and do we know how fast.

## What was built

- **One correlation id through all five services.** The scenario sends one id on every call; each service logs one JSON line per request with it; a check script counts it in each service's log. Verified on the cloud: one run's id appeared in all five.
- **Service level objectives as code.** An availability objective per service and a latency objective for the two services with no language model in the path, on Cloud Run's own metrics (free), each with a fast-burn alert. Created by Terraform and tested with a mocked provider in CI.
- **Four failure drills on the real cloud, and a matrix of them in CI.** Stop the ledger database VM; pause Pub/Sub delivery to the audit service; restore the ledger from its daily backup; redeploy the assistant while an approval waits.
- **Approval recovery.** An approval survives a restart and a redeploy and posts exactly once; an approval nobody answers expires after 24 hours (HTTP 410), posting nothing.

## What was measured

| Drill | Result |
|---|---|
| Ledger VM stopped | health went to no answer; **40 s** from the start request to healthy again, no repair by hand; the scenario failed during the outage and passed after |
| Pub/Sub paused | the scenario failed at the audit step while paused and passed after the restore; events waited, none were lost |
| Backup restored | the dump was a valid gzip and restored to **54 settlements, equal to the live 54**, in 31 s |
| Redeploy mid-approval | an approval made on revision 00018 was approved 12 minutes later on 00019, posted once, closed the reconciliation exception, left the ledger balanced |
| Settlement SLOs after the outage | 40.7 % of the availability error budget and 60.5 % of the latency budget left: the drill is visible in the budget |

## What went wrong, and what each failure taught

1. **A scenario that consumes finite resources fails for reasons unrelated to the code.** The 150,000 EUR test payment drained a seeded ledger account after about six runs; the orders drained the seeded stock after about sixteen. Both showed up as "step N failed", and both were fixed by design (the payment alternates between two accounts; stock is topped up to par once a day), not by hiding the failure.
2. **A safety check that works can still be the thing that fails the test.** The assistant refused a write-off on the wrong settlement three times, in three different ways: a model that chose another settlement of the same amount; two equally good candidates; a settlement that reconciliation never offered. Each time the refusal was the system behaving correctly; each time the real defect was upstream (the prompt did not name the settlement, the choice was ambiguous, my own change had left the settlement open).
3. **I introduced a defect in Phase A, and Phase B found it.** Closing an exception because the assistant had posted the adjustment never consumed the settlement's open item, so open items piled up and reconciliation, which compares a line only with the oldest of them, stopped finding the current run's settlement. It surfaced as a model "failing" at the proposal step. The correlation id made it a few minutes of reading logs instead of a hunt, and the fix came with a test that fails without it.
4. **A drill designed with the wrong assumption still taught something.** The first restore ran from the database VM and failed: the VM's account can write backups but not read them, on purpose. The drill was redone the way an operator would, and the failed attempt is the proof that the backup path is least-privilege.
5. **Over-reading a green result.** A scorer printed `pass` when the model had never answered, because nothing unsafe had happened. It now counts such a trial as a fallback, which changed what the model comparison could honestly claim.

## What changed because of it

The scenario no longer drains anything; reconciliation consumes the open item it closes; the assistant's prompt names the settlement a request names, and a policy check refuses a proposal that does not match the bank line or that is ambiguous; approvals expire; the image has no `pip` in the runtime (a scanner finding that took three attempts to locate); and every service writes the correlation id.

## What remains, and what this does not show

- Traffic here is small (a scenario run is a few dozen requests), so an objective's percentage swings on a handful of requests. The numbers show the mechanism works, not a service's real reliability.
- Four drills on one deployment are not a reliability programme. There is no load test, no regional failure, no chaos in production.
- Cloud Trace spans, a log-based token and fallback metric, and a shorter database connection timeout (30 s today, so an outage makes requests hang rather than fail fast) are recorded but not done.
- The audit-feed drill's delivery latency was not captured in the cloud shell on the day.
- One author, one project, simulated customer.

## Where to look

`docs/DRILLS.md` (how each drill is run), `docs/DRILL_RESULTS.md` (the numbers and the failures), `docs/EVIDENCE.md` (the dated captures), `landscape/trace_check.sh`, `landscape/observability/`, `tests/test_approval_recovery.py`.
