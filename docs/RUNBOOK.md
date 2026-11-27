# Runbook: cutover to Google Cloud, and operating the landscape

*Hub design note GCP-01, Section 9, with the commands. Everything before this runbook was built and tested on stand-ins (emulators, a PostgreSQL container, the simulated model); this is the one-time move onto a real Google Cloud project, on the free tier, and what to do when something goes wrong. Check each Google limit on Google's own pages at sign-up: free allowances and regions change, with notice.*

> **Rule.** Never upgrade the account to a paid plan, and never put a key, a token or a password into a file in a repository. Secrets live in Secret Manager; the values you type below go to Secret Manager only.

## 0. What the free tier means for the schedule

- The **free trial** gives a credit for 90 days. Within the trial the whole landscape runs on real Google Cloud at no cost: this is the window to deploy, test and record the evidence.
- **Always Free** allowances need an active billing account, and **when the trial ends Google stops the resources unless the account is upgraded**. The plan rules out upgrading, so the infrastructure is destroyed before the trial ends (Section 9) and stays reproducible from the repositories.
- The **Gemini API key is independent of Cloud billing** and keeps working on its own free tier, with its per-minute and per-day limits. The trial credit does not pay for it.

## 1. Account, project and budget (about 20 minutes, by hand)

1. Create a dedicated Google account and start the free trial (it asks for payment details to prove you are a person; you are not charged without an explicit upgrade).
2. In the Cloud console create a project, for example `finance-ai-landscape`. Note its **project id** (not the display name).
3. In AI Studio create a **Gemini API key**, and note which free models and limits your account shows.
4. Billing, Budgets and alerts: one budget at 1 USD (or your currency) with alerts at 50 and 100 percent. This is only an alert; `landscape/foundation` adds a second one at the first cent.
5. Open **Cloud Shell** (the terminal icon in the console). It has `gcloud`, `terraform`, `git` and `docker`, and keeps your home directory, which holds the Terraform state until Section 4.

## 2. Fill in the placeholder files

Clone the four repositories in Cloud Shell and edit the `.vars` files. Each placeholder is the text `PLACEHOLDER` or an example address.

```bash
git clone https://github.com/subhamviky/enterprise-finance-genai-assistant
git clone https://github.com/subhamviky/financial-settlement-platform
git clone https://github.com/subhamviky/payment-reconciliation-engine
git clone https://github.com/subhamviky/order-to-cash-agentic-ai
cd enterprise-finance-genai-assistant
```

| File | What to set |
|---|---|
| `deploy/gcp/landscape.vars` | `GCP_PROJECT_ID`; `GCP_REGION` (keep `us-central1` unless you choose `us-west1` or `us-east1`); `GITHUB_OWNER`; optionally `BILLING_ACCOUNT` (from Billing) and `BUDGET_CURRENCY`; `E2A_PROVIDER_PROFILE` (`simulated`, or `gemini_api` once the key exists) |
| each repository's `deploy/gcp/binding.vars` | the project id wherever `finance-ai-landscape-PLACEHOLDER` appears; `INVOKER_MEMBERS` (the Google accounts of the people, and the services' accounts); the `*IDENTITY_SUBJECT_ROLES` maps (who may do what). Four eyes needs **two different people**: an investigator and an approver |

The service accounts have fixed names: `genai-app`, `recon-app`, `audit-app`, `o2c-agent-service-dev` and `settlement-app`, each `@<project id>.iam.gserviceaccount.com`. Replace the project id in them; nothing else changes.

`landscape/tfvars.py` turns these files into Terraform inputs, one stack at a time (Section 6). A line it prints as a warning means a placeholder is still there.

## 3. First commands

```bash
PROJECT=your-project-id
gcloud config set project "$PROJECT"
gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com iam.googleapis.com
```

## 4. The foundation (once)

```bash
cd landscape/foundation
python3 ../tfvars.py foundation --landscape ../../deploy/gcp/landscape.vars --out terraform.tfvars.json
terraform init && terraform apply
terraform output
```

It enables the APIs and creates the image repository, the one free Firestore database, the state bucket, GitHub deployment through Workload Identity Federation, the budget alert, the secret for the Gemini key (without a value) and the two stand-in accounts of the scenario. Keep its outputs.

**State.** The stacks keep their Terraform state in the working directory, which Cloud Shell preserves; do not delete it, you need it to destroy (Section 9). **To keep it in the bucket instead (recommended once the stacks exist), run `PROJECT=your-project-id bash enterprise-finance-genai-assistant/landscape/move-state.sh` from the folder that holds the four repositories**: it does what follows for all six stacks (a `backend_override.tf` in each, kept out of commits, then `terraform init -migrate-state`). By hand, add this file to a stack directory, then run `terraform init -migrate-state`:

```hcl
# backend_override.tf (not committed)
terraform {
  backend "gcs" {
    bucket = "YOUR-PROJECT-ID-tfstate"
    prefix = "the-stack-name"
  }
}
```

## 5. Secrets and images

```bash
# the Gemini key (only with the gemini_api profile): the value never touches a file
printf '%s' 'PASTE-THE-KEY' | gcloud secrets versions add gemini-api-key --data-file=-

# the images: one repository for all five, from the foundation's output image_repository
REPO=us-central1-docker.pkg.dev/$PROJECT/landscape
gcloud auth configure-docker us-central1-docker.pkg.dev

# the ledger's PostgreSQL image, mirrored (the ledger VM has no external IP)
docker pull postgres:16-alpine
docker tag postgres:16-alpine "$REPO/postgres:16-alpine" && docker push "$REPO/postgres:16-alpine"

# the five services (add --build-arg POETRY_EXTRAS=gemini to the Python ones with the gemini_api profile)
for pair in \
  "financial-settlement-platform/settlement-service settlement-service" \
  "financial-settlement-platform/audit-ai-service audit-ai-service" \
  "payment-reconciliation-engine/reconciliation-service reconciliation-service" \
  "order-to-cash-agentic-ai/o2c-agent-service o2c-agent-service" \
  "enterprise-finance-genai-assistant/genai-assistant-service genai-assistant-service"; do
  set -- $pair
  docker build -t "$REPO/$2:latest" "../../../$1" && docker push "$REPO/$2:latest"
done
```

The paths assume the four repositories are cloned side by side and you are in `landscape/foundation`; adjust `../../../` otherwise. Docker Hub and the base images are reached from Cloud Shell; the Java builds fetch E2A from its tag (needs the tags `v1.11.0` of E2A and `v0.2.0` of e2a-managed-providers to exist).

## 6. The services, in this order

For each stack: write its inputs, then apply. **Settlement first, with its database password before its VM boots.**

```bash
# settlement (the ledger VM and the service)
cd ../../../financial-settlement-platform/settlement-service/infra/gcp
python3 ../../../../enterprise-finance-genai-assistant/landscape/tfvars.py settlement \
  --landscape ../../../../enterprise-finance-genai-assistant/deploy/gcp/landscape.vars \
  --binding ../../../deploy/gcp/binding.vars --out terraform.tfvars.json
terraform init
terraform apply -target=google_secret_manager_secret.db_password          # the secret, without a value
openssl rand -base64 24 | tr -d '\n' | gcloud secrets versions add settlement-db-password --data-file=-
terraform apply                                                           # the VM reads the password at boot
terraform output
```

Then, the same way (the stack directory, `tfvars.py STACK --landscape ... --binding ...`, `terraform init`, `terraform apply`):

| Order | Stack | Directory | `tfvars.py` argument |
|---|---|---|---|
| 2 | reconciliation | `payment-reconciliation-engine/reconciliation-service/infra/gcp` | `reconciliation` |
| 3 | audit-ai | `financial-settlement-platform/audit-ai-service/infra/gcp` | `audit` (binding: the settlement repository's) |
| 4 | order-to-cash | `order-to-cash-agentic-ai/o2c-agent-service/infra` | `o2c` |
| 5 | the assistant | `enterprise-finance-genai-assistant/genai-assistant-service/infra` | `assistant` |

**Callers that do not exist yet.** A Cloud Run `run.invoker` grant to a service account that has not been created fails with `Service account ... does not exist`. Settlement is applied first, before `recon-app`, `genai-app`, `audit-app` and `o2c-agent-service-dev` exist, so for the first round of applies give reconciliation, audit-ai, O2C and settlement only the deployer account in `INVOKER_MEMBERS`; when all five stacks exist, restore the full lists and apply those four stacks again (they only add grants). The assistant's callers (the two people and the scenario accounts) exist from the foundation and can be set from the start.

**First apply of settlement.** Cloud Run and the ledger VM are created in parallel, so the service may fail its start-up check before the database accepts connections. Wait a minute and apply again. The password secret is read by the VM and by Cloud Run; store it **without a trailing newline** (`tr -d '\n'`, as above): PostgreSQL strips one when it reads a password file and Cloud Run does not, and with a newline the service is refused with `password authentication failed`.

After each apply, copy the service's Cloud Run URL (`terraform output`; O2C prints it as `service_uri`) into `deploy/gcp/landscape.vars` and into the bindings that name it (`SETTLEMENT_API_URL`, `RECONCILIATION_API_URL`, `AUDIT_API_URL`, `O2C_API_URL`), then re-apply the stacks that call it. Settlement's URL is needed by reconciliation, audit-ai, O2C and the assistant; do the first round of applies, fill in the URLs, and apply the four again.

The free tier allows **three** Cloud Scheduler jobs for the whole account; the landscape uses exactly three (settlement's maintenance, reconciliation's run, O2C's combined job).

## 7. The scenario against the cloud

1. Repository variables for `enterprise-finance-genai-assistant` (Settings, Secrets and variables, Actions, Variables): `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOYER_SA` (foundation outputs `workload_identity_provider` and `deployer_service_account`), the five `*_API_URL`, and `SCENARIO_INVESTIGATOR_SA` and `SCENARIO_APPROVER_SA` (output `scenario_service_accounts`).
2. Make the two scenario accounts the two people: put them in the assistant's `INVOKER_MEMBERS` and `IDENTITY_SUBJECT_ROLES` (`tenant:acme` and `investigator` or `finance-approver`), and give `genai-app` its roles in the other systems' maps; apply the assistant and the systems again.
3. Actions, `landscape-gcp`, **Run workflow**, `target: cloud` (not "Re-run jobs": that repeats the old commit). The steps and their results are in the run summary; keep it as evidence. Each run uses its own orders, bank lines and amounts, so the scenario can be repeated on the same landscape; step 7a (the requester approving their own proposal) runs only in the local run, because with real identities the approver account is a second person.

Repository variables hold **values**, not descriptions: `GCP_WORKLOAD_IDENTITY_PROVIDER` is the whole `projects/NUMBER/locations/global/workloadIdentityPools/.../providers/...` string from `terraform output -raw workload_identity_provider`. Changing the assistant's code needs a new image and a new revision: build and push with `--build-arg POETRY_EXTRAS=gemini`, then `gcloud run services update genai-assistant-service --region us-central1 --image REPO/genai-assistant-service:latest` (Terraform does not redeploy an unchanged tag).

## 8. Verify

| Check | How | Expected |
|---|---|---|
| Nothing is public | `gcloud run services list`, then `gcloud run services get-iam-policy NAME --region us-central1` | no `allUsers` |
| Free resources only | console, Billing, Reports | a cost of 0 for the project |
| The state is where it should be | console, Firestore | collections `o2c`, `audit`, `recon_*`, `genai` in `(default)` |
| Scheduler | `gcloud scheduler jobs list --location us-central1` | three jobs |
| The assistant | the scenario's step table | all steps pass |
| Latency and cold start (G-4, G-3 of the design document) | run the evaluation with `E2A_PROVIDER_PROFILE=gemini_api` and `E2A_SWAP_LIVE=true`; read `gcloud logging read` for request latency | record p50 and p95 |

**Running the 62-case sets against the real model** (about 190 model calls, inside the free daily limit of 500 and about 15 minutes at the process's 12 requests a minute; the four systems are the in-memory stand-ins, only the model is live). The key is read from Secret Manager into this one command's environment, never into a file:

```bash
cd ~/enterprise-finance-genai-assistant/genai-assistant-service
python3 -m venv ~/venv-gate && . ~/venv-gate/bin/activate
pip install --quiet -e ".[gemini]" pytest
GEMINI_API_KEY="$(gcloud secrets versions access latest --secret=gemini-api-key)" \
E2A_PROVIDER_PROFILE=gemini_api LLM_MODEL_ID=gemini-3.5-flash-lite \
LLM_MAX_RPM=12 GEMINI_MAX_REQUESTS_PER_DAY=400 LLM_SDK_TIMEOUT=30 LLM_SDK_MAX_RETRIES=1 \
python -m genai_assistant_service.release.gate --skip-tests --report ~/live-gate-report.json | tail -40
```

Expect some cases to fail on wording: the golden set's `contains` checks were written for the simulated model's phrasing (for example "short by 2.50"), so a correct answer in other words fails them. Read the report for what each failure was (wording, a refusal, a degraded answer after a 503) before judging the model.

Measured on 25 November 2026 (the first passing cloud run, `docs/EVALUATION_REPORT.md`): the whole scenario took about 125 seconds; every step without a model call about one second; the two steps with a model call 79 and 24 seconds on the free-tier `gemini-3.5-flash-lite`; billing 0.00 of the trial credit.

## 9. Teardown, before the trial ends

The trial started on 25 November 2026 and lasts 90 days, so it ends on or about **23 February 2027**; plan the evidence capture and the teardown for the week of 8 February 2027 (Billing shows the exact days left).


In reverse order, from each stack directory: `terraform destroy`. Then the foundation (`force_destroy` is on for the state bucket, and the Firestore database is set to be deleted). Delete the repository variables, the Workload Identity provider and the Gemini key's secret. Keep the evidence: the scenario summary, the evaluation report, the billing report, screenshots. The Gemini API key itself stays valid.

## 10. Operating

| Situation | Action |
|---|---|
| A bad revision | `gcloud run services update-traffic NAME --to-revisions=PREVIOUS=100 --region us-central1` (a rollback is a traffic move; it creates nothing) |
| Gemini 429 or the daily quota spent | nothing to do: investigations degrade to the verified facts and proposals are withheld (design document, Section 10); the quota resets daily; or set `E2A_PROVIDER_PROFILE=simulated` and apply |
| An approval stuck | `GET /api/v1/approvals?status=PENDING` as an approver; a decision is final; a new proposal is a new approval |
| A posting with an unknown outcome | ask again with the same proposal: the same idempotency key returns the first result; settlement-service's own maintenance job recovers stuck settlements |
| Scale to zero makes the first request slow | expected (cold start); the Java service is the slowest; do not set a minimum instance (it is not free) |
| Logs | `gcloud logging read 'resource.type="cloud_run_revision"' --limit 50`; metadata only, never prompts |
| Rotate the Gemini key | add a new secret version; the service reads `latest` at start-up; disable the old version |

## 11. If something fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `terraform apply`: API not enabled | the foundation has not finished or an API was added | apply the foundation again |
| Cloud Run: image not found | an image was not pushed, or the tag differs | push it (Section 5); the tag in `binding.vars` must match |
| 403 between services | the caller's account is missing from the callee's `INVOKER_MEMBERS` or `*SUBJECT_ROLES` | add it, apply the callee |
| The ledger service does not start | no password version, or the VM cannot reach Artifact Registry | add the version, restart the VM (`gcloud compute instances reset`); check the mirrored image exists |
| 401 from the assistant | the token's audience is not the assistant's URL | mint it with `--audiences=<the URL>` |
| Pub/Sub messages pile up | audit-ai refuses the push | check its `run.invoker` for the push account; the dead-letter subscription holds the messages |
| `Error acquiring the state lock` | an earlier `terraform apply` is still running (often waiting at `yes` in another Cloud Shell tab) or was cut off | find the other tab, or `kill -INT PID` (never `kill -9`); only if no terraform runs, `terraform force-unlock ID` |
| `Service account X does not exist` on a `run.invoker` grant | the caller's stack has not been applied yet | Section 6: deployer only for the first round, full lists last |
| The ledger service: `password authentication failed for user "settlement"` | the password secret has a trailing newline | add a new version without it (`tr -d '\n'`), apply |
| 403 `issuer 'accounts.google.com' is not trusted` | a person's Google token spells the issuer without `https://` | trust both spellings in `E2A_IDENTITY_TRUSTED_ISSUERS` (the assistant's Terraform does) |
| 403 `the caller is not granted tenant 'acme'` | the caller's token has no e-mail (the map is keyed by e-mail) | ask for the e-mail in the token (`id_token_include_email: true` in the workflow; the metadata server's `format=full` for a service) |
| An investigation answers `NOT_FOUND` or takes over a minute | the free-tier model is busy (503) or wrapped its JSON in a code fence | the assistant now bounds each model call at 12 seconds and reads fenced JSON; if it still degrades, wait or switch the profile |
| A repeat of the scenario fails at the statement or at the proposal | an earlier run's lines or open items of the same amount | the scenario uses its own data per run; pull the current `landscape/scenario.py` |
| Billing shows a charge | something outside the free tier | find it in Billing, Reports, group by SKU; destroy it; do not upgrade |


## Closing the exception after an approved write-off (GCP-02 A.1)

After the ledger shows the adjustment, the assistant calls reconciliation's `POST /service/v1/exceptions/{line_id}/resolve`. Grant the assistant's service account the role `reconciliation.resolve` in the reconciliation stack's `identity_subject_roles` (next to `tenant:acme` and `reconciliation.read`), then re-apply that stack and redeploy both images. Without the grant the call is refused (403): the posting still stands, the exception stays open and the receipt says so.

## Multi-trial live evaluation (GCP-02 A.2)

`landscape/live_trials.py` runs six scenarios N times each against the stand-ins with the live model, and checks facts (what was posted, on which settlement and amount, whether the exception closed, nothing written before approval) instead of wording. A trial is `pass`, `fallback` (the system stayed safe but the model gave no usable draft) or `wrong-fact`; a 429 stops the run and the report says where. From `genai-assistant-service`, with the gate's environment (`E2A_PROVIDER_PROFILE=gemini_api`, `GEMINI_API_KEY`, `LLM_MODEL_ID`):

```bash
python ../landscape/live_trials.py --trials 5 --pause 15 --report trials-$(date +%F)-$LLM_MODEL_ID.json
```

Five trials of the six scenarios is about 50 model requests and 8 minutes. Free-tier limits apply per project per day (see the model table in the GCP-02 plan); run one model per day and keep the report, which names the model, date, trials and pause.

## Following one run through the services (GCP-02 Phase B, item 3)

The scenario sends one `X-Correlation-Id` (`scenario-<run>`) on every call and prints it at the end. The four Python services log one JSON line per request with it (`event: http_request`), the assistant sends it on every call to the other systems, and settlement-service reads it. After a cloud run, in Cloud Shell:

```bash
~/enterprise-finance-genai-assistant/landscape/trace_check.sh scenario-<run>
```

It counts the entries in each of the five services' logs; every service should show at least one. The traces in Cloud Trace need the OpenTelemetry exporter, which is a later step of Phase B.

## The scenario buys goods: stock (and the ledger) are finite

Each scenario run buys 3 printers and 2 to 21 scanners from O2C, whose stock is seeded once (50 printers, 200 scanners), and moves 150,000 EUR between two ledger accounts. After about 16 runs the printers are gone and step 1 fails with orders `REFUSED` ("insufficient stock"; the step prints the reason). For this landscape, set `daily_restock = true` in the O2C stack (Terraform variable; it sets `O2C_DAILY_RESTOCK=true`): each SKU is topped up to its catalog level once a day. Until the stack is applied, the same effect with no Terraform: `gcloud run services update o2c-agent-service-dev --region us-central1 --update-env-vars O2C_DAILY_RESTOCK=true` (a new revision starts and tops the stock up). Where stock is real, leave it off.
