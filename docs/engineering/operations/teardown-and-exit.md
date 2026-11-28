# Teardown and exit plan

- **Status:** Reviewed 2026-11-28 · **Platform document.** Trial started 25 November 2026 and ends about 23 February 2027. Evidence capture and teardown are planned for the week of 8 February 2027.

## What outlives the cloud

The repositories, the Terraform stacks, the tests, the documents, the captured evidence and the case studies. Nothing about the project depends on the cloud project still existing; the cloud was a means of producing evidence.

## Before destroying (export)

| Keep | How |
|---|---|
| Scenario summaries and the final green run | the workflow run page and its summary, saved as images or text under `docs/assets/evidence` |
| Evaluation results (multi-trial reports, model comparison, measurements) | the JSON reports and `docs/EVALUATION_REPORT.md` |
| SLO screenshots and the metrics explorer view | Cloud Monitoring screenshots |
| Billing report showing 0.00 | screenshot |
| Drill results and timings (including a timed destroy and rebuild) | `docs/DRILL_RESULTS.md` |
| Terraform state | move to the gcs backend first (`landscape/move-state.sh`) so the destroy is repeatable, then destroy |
| The Gemini key | it stays valid after the project is gone |

## Order of destruction (reverse of creation)

1. Stop traffic and scheduled jobs (pause the three Scheduler jobs).
2. `terraform destroy` per stack, in reverse order: the observability stack, the assistant, order-to-cash, audit-ai, reconciliation, settlement (ledger VM, backup bucket, secrets), then the foundation (the state bucket has `force_destroy`; the Firestore database is set to be deleted).
3. Delete the repository variables and secrets in the four GitHub repositories.
4. Delete the **Workload Identity Federation provider** and pool, and the Gemini key's secret.
5. Delete the project (or let the trial lapse), then check the Billing page shows no active billing account charges.

## Verification after teardown

`gcloud projects describe`, `gcloud run services list`, `gcloud compute instances list`, `gcloud firestore databases list` return nothing (or the project is gone); the Billing report shows 0.00; `gh variable list` is empty in each repository; the workflows' cloud jobs are disabled or expected to fail.

## What stops working in the repositories

The `landscape-gcp` cloud target, `ops` and `promote` need the project; the local target of `landscape-gcp` (emulators, stand-ins), all unit and adversarial tests, the Terraform mock-provider tests and the release gate keep working. The README states this so a reader does not take a red cloud job for a defect.

## Rebuild

RUNBOOK sections 1 to 8 recreate everything from git in about the order and time recorded by the Phase D rebuild drill (to be filled in).
