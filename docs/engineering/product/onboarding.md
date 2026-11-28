# Onboarding: your first day on this repository

- **Status:** Draft 2026-11-28, awaiting owner review

## Read, in this order (about 90 minutes)

1. `README.md` and `SECURITY.md` (what this is; synthetic data only).
2. [Solution overview](solution-overview.md), then `docs/design/GENAI_ASSISTANT_DESIGN.md` sections 1 to 5 and 8.
3. [ADR index](../adr/README.md): skim the titles, read 0001, 0007, 0009, 0017.
4. `docs/case-studies/phase-b-reliability-and-operations.md` and `phase-c-customer-shaped.md` (what failed and why).
5. `docs/RUNBOOK.md` sections 7, 8 and 10.

## Run it locally (no cloud account)

```bash
cd genai-assistant-service
poetry install
poetry run pytest -q                         # 176 tests, about 5 seconds, simulated model
poetry run python ../landscape/measure.py --runs 1 --compare     # model calls per request, offline
```

The simulated model needs no key. To use the real model: `E2A_PROVIDER_PROFILE=gemini_api`, `GEMINI_API_KEY`, `LLM_MODEL_ID` (free tier; see [cost and capacity](../operations/cost-and-capacity.md) before running anything live).

## Map of the code

| You want to change... | Look in |
|---|---|
| what the assistant may propose, per customer | `policies/governance.yaml`, `policies/customers/`, `services/policy.py` |
| how a request is classified | `agents/intent_agent.py` |
| which facts are read | `agents/evidence_agent.py`, `tools/catalog.py` |
| how answers are checked | `agents/investigator_agent.py` |
| approvals and expiry | `services/stores.py`, `services/assistant.py`, `workflow/investigation_workflow.py` |
| the customer's documents | `policies/documents/`, `services/documents.py` |
| the HTTP API | `routers/api.py`, [API reference](../api/API.md) |
| infrastructure | `genai-assistant-service/infra`, `landscape/observability` |
| pipelines | `.github/workflows/` |

## Working agreements

- One concern per branch; run the tests before pushing; CI must be green to merge.
- Add a regression test for every bug, and an [ADR](../adr/0000-template.md) for every decision you would have to explain later.
- A finding from a live run or a drill becomes a test and, if it cost real time, a [post-incident review](../postmortems/TEMPLATE.md).
- Never use real data. Never upgrade the cloud trial. Never put a key in the repository.
- Cloud actions go through the workflows (`ops`, `promote`, `landscape-gcp`); Terraform applies are the owner's, from Cloud Shell.

## Who to ask

The repository owner (the only maintainer). Open a GitHub discussion or an issue for questions; report vulnerabilities privately (`SECURITY.md`).
