# Engineering records

How this project is decided, secured, operated and learned from. The design document says *what* the system is; these say *why it is that way*, *how it fails*, *how it is run* and *what we learned*.

| Area | Document |
|---|---|
| Decisions | [Architecture decision records](adr/README.md) (23) |
| Learning from failure | [Post-incident reviews](postmortems/README.md) (10) |
| Security | [Threat model](security/threat-model.md), [data classification](security/data-classification.md), `SECURITY.md` |
| Reliability | [SLOs and error-budget policy](operations/slo-and-error-budget.md), [incident response](operations/incident-response.md), [disaster recovery](operations/disaster-recovery.md) |
| Delivery | [Release process](operations/release-process.md), `CHANGELOG.md` |
| Cost and lifecycle | [Cost and capacity](operations/cost-and-capacity.md), [teardown and exit plan](operations/teardown-and-exit.md) |
| Quality | [Test strategy](testing/test-strategy.md), `docs/DRILLS.md`, `docs/EVALUATION_REPORT.md` |
| Interfaces | [API reference](api/API.md) |
| Product | [Requirements and user stories](product/requirements-and-user-stories.md), [solution overview](product/solution-overview.md), [onboarding](product/onboarding.md) |

**Platform documents.** Five repositories share one deployment, one set of workflows (`landscape-gcp`, `ops`, `promote`), one observability stack and one teardown, so the platform documents (SLO policy, incident response, release process, disaster recovery, cost and capacity, teardown) live here once (ADR 0023). The other repositories carry the documents that are about their own service and link back.

Conventions: Markdown; dated, with a status; no private data; claims name their evidence; honesty about limits is part of the document.
