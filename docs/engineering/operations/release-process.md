# Release process

- **Status:** Draft 2026-11-28, awaiting owner review · **Platform document** (the workflows live in this repository and act on all five services).

## Versioning

Each repository keeps a `CHANGELOG.md` (Keep a Changelog format). The assistant has no packaged release number: a release is a **commit on `main`** and the Cloud Run **revision** built from it (the image is tagged by its commit). The frameworks (E2A, A2C, e2a-managed-providers) use semantic versions and tags.

## From change to production

1. **Branch and pull request.** One concern per branch; the author runs the tests locally first. `main` accepts changes through merged pull requests.
2. **CI on the pull request** (`genai-assistant-service ci`): unit, adversarial, isolation and journey tests; the same tests again with state in the Firestore emulator; strict E2A conformance; the release gate and its report (kept as an artifact); Terraform fmt, validate and test for each stack against a mock provider.
3. **Merge to `main`** runs the delivery pipeline (`genai-assistant-service delivery`): tests, IaC checks, image build with a Trivy vulnerability scan. The pipeline's own deploy job is switched off; deploying is a deliberate act (step 4).
4. **Promote** (Actions, `promote`, Run workflow; usable from a phone):
   1. build the image tagged by commit and create a revision with **no traffic**, reachable on its own tag URL;
   2. shift **10%** to it;
   3. run the **14-step scenario against the candidate's tag URL** (the gate);
   4. shift **100%**;
   5. run the scenario again through the service URL;
   6. on any failure after traffic moved, **roll back** to the previous revision automatically.
5. **Verify.** Read the run summary (previous and new revision, gate results), and for changes that touch behaviour run the multi-trial live evaluation (`landscape/live_trials.py`) on the same model and date as the comparison you quote.

## Rollback

Automatic when a gate fails. Manual at any time:

```bash
gcloud run services update-traffic genai-assistant-service --region us-central1 --to-revisions <previous revision>=100
```

A broken environment variable on a candidate persists in the service template; the rollback job therefore also writes a clean no-traffic revision (only for the `break` drill). If you roll back by hand after a bad setting, do the same.

## Emergency and rebuild paths

`ops deploy` builds one service from its repository and gives it a new revision **straight to 100%** with no canary. It is for rebuilding and for services other than the assistant, not for changes that matter. Terraform applies are done by the owner in Cloud Shell (the deployer cannot administer monitoring or read logs, on purpose).

## Change classification

| Change | Path |
|---|---|
| code or policy of the assistant | PR, CI, `promote` |
| a customer's policy file or documents | PR, CI (the documents are compared with the policy), `promote` |
| infrastructure | PR (Terraform tests), apply by the owner |
| a document only | PR; no deploy |

## Not covered

No feature flags beyond environment switches (`GENAI_INTENT_BY_RULES`), no staged regional rollout, no change advisory board: there is one author and one environment.
