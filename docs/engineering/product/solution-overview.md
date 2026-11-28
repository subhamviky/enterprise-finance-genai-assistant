# Solution overview

*A one-page summary for a customer or hiring manager. Synthetic data, simulated customers, one author, a free-tier cloud and a free-tier model; the claims below name the evidence.*

## The problem

A finance team receives a bank payment that does not match an open invoice. An investigator opens a reconciliation tool, a ledger, an audit view and an order system to find out why (usually a short payment or a fee), then asks a colleague to approve a write-off or refund. It is slow, it is easy to approve the wrong thing, and every step is manual.

## What it does

A **GenAI assistant** reads the four systems, explains the cause with citations, proposes the fix, and waits for a **second person** to approve it. Only then does it post one adjustment to the ledger, read it back, and close the exception.

- **Grounded.** Every statement cites a record that was read; a figure not in the evidence is refused.
- **Safe by construction.** The model cannot move money. Code validates every proposal (limits, currency, the exact gap, the right settlement), a different person approves, and the post is idempotent.
- **Customer-shaped.** Limits, currencies, roles, number of approvers, decision window, masking and policy documents come from a configuration file per customer.
- **Operable.** One id follows a request through five services; SLOs and alerts exist; failures were rehearsed and timed; releases are gated and roll back by themselves.

## How it is built

Five services on Google Cloud (the assistant, a settlement ledger, a reconciliation engine, an audit service and an order-to-cash service) on a **free tier, never paid**, built on a family of frameworks (E2A for agent runtime and governance, A2C for scaffolding). A free-tier Gemini model does the language work, and every agent can fall back to verified facts.

## What was measured (from the repository's own evidence)

| Claim | Evidence |
|---|---|
| End-to-end scenario passes against the deployed services | 14 of 14 steps on the real cloud (`landscape-gcp`, `docs/EVALUATION_REPORT.md`) |
| Recovery without manual repair | ledger back in **40 s**; event feed in **10 s**; a mid-approval redeploy loses nothing (`docs/DRILL_RESULTS.md`) |
| Backups restore | 54 of 54 settlements in 31 s |
| Hostile input causes no action | 45 adversarial cases, one real firewall gap found and fixed (post-incident review 0010) |
| Customers do not see each other | 24 tenants, a noisy neighbour refused while a quiet one is served |
| Cheaper per request | intent read by rules: model calls per plain request 2 to 1 (simulated); live figures in the evaluation report |

## What it is not

Not a product: no UI, no real data, no multi-region, no load test, one author. The other four services serve one tenant per deployment, so a second customer is proven on stand-ins, not on the live ledger.

## Where to look

`docs/design/GENAI_ASSISTANT_DESIGN.md` (design), `docs/case-studies/` (what happened and what it taught), `docs/engineering/` (decisions, incidents, security, operations).
