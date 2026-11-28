# Incident response and on-call runbook

- **Status:** Reviewed 2026-11-28 · **Platform document.** The landscape has one operator (the repository owner) and no pager; this is how an incident would be run by a team, scaled down. Day-to-day operation is in `docs/RUNBOOK.md`; failure rehearsals are in `docs/DRILLS.md`.

## Severity

| Level | Meaning | Response target | Example |
|---|---|---|---|
| SEV-1 | money moved wrongly, or data crossed a tenant | stop posting at once; owner engaged immediately | a write-off posted without approval; one tenant reads another's approval |
| SEV-2 | a customer-visible wrong or blocked outcome | within the hour | exceptions not closing; the assistant refusing every proposal |
| SEV-3 | degraded or blocked internal process | same day | the scenario failing; the model degraded |
| SEV-4 | near miss or a test failing for its own reasons | next working day | a drill failing by design |

## Roles

**Incident commander** (decides, keeps the timeline), **operator** (runs the commands), **scribe** (writes the timeline), **communications** (tells the stakeholder). One person may hold all four; the roles still separate *deciding* from *doing* in the notes.

## First 10 minutes

1. **Stop the harm.** If an adjustment is wrong: take the assistant out of traffic (`gcloud run services update-traffic genai-assistant-service --region us-central1 --to-revisions <last good revision>=100`) or, if it is the ledger, stop the assistant first, not the ledger.
2. **Find the run.** Every request carries `X-Correlation-Id`. `landscape/trace_check.sh <id>` (Cloud Shell) counts that id in all five services' logs; a scenario prints its id at the end.
3. **Open a timeline** (a post-incident review draft from `docs/engineering/postmortems/TEMPLATE.md`) and write down what you saw, with times.
4. **Decide the severity** from the table.

## By symptom

| Symptom | Likely cause | Check | Action |
|---|---|---|---|
| Scenario step 1: orders REFUSED, "insufficient stock" | O2C stock used up (once-a-day top-up already spent) | the step prints the reason | wait for 00:00 UTC, then force a new O2C revision (RUNBOOK) |
| Settlement health `000` or a hang | ledger VM stopped or the database not up | `gcloud compute instances list` | `gcloud compute instances start ledger-db --zone us-central1-a`; recovery took 40 s in drill 1 |
| Scenario fails at step 2 (audit finding never arrives) | Pub/Sub push to audit-ai paused or broken | `gcloud pubsub subscriptions describe audit-settlement-events` | restore the push endpoint, service account and audience (drill 2); backlog drains in about a minute |
| Assistant answers `degraded` for everything | model quota (429), model busy (503), or a model that rejects a feature | `assistant_answers` by `degraded`; the service log's `LLM inference failed` | wait for the quota, switch `LLM_MODEL_ID`, or accept the fallback (facts only) |
| Approval returns 410 | the approval expired (24 h or the customer's window) | the approval's status | ask again; nothing was posted |
| Approval returns 403 | requester approving their own, or not the approver role | the approval record | a second person with the approver role |
| Exceptions stay open after an approved write-off | reconciliation down or refusing the resolve; the receipt says so | the receipt's `exception` field; reconciliation log | the posting stands; re-run `resolve` once reconciliation is back |
| `promote` failed | a gate failed; `rollback` should have run | the run summary | confirm the previous revision serves 100% (`gcloud run services describe ...`) |
| Delivery pipeline red on the image scan | a vulnerability in the runtime image | the scan's "Where is the finding?" step | see post-incident review 0005 |
| Budget alert at ₹1 | something is billable | Billing report | stop the resource; the trial is never upgraded |

## After

Within two working days: a [post-incident review](../postmortems/README.md) (blameless: causes are system conditions, not people), action items with owners and a type (prevent, detect, mitigate), the runbook or drill updated if the symptom table was wrong, and an ADR if a design decision changed.
