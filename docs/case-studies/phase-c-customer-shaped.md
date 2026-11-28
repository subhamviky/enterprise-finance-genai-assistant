# Case study: making the assistant customer-shaped and shippable (GCP-02 Phase C)

*Simulated customers, real cloud: a GenAI assistant that investigates bank-line exceptions and proposes write-offs that a second person approves, on the free tier of Google Cloud. Dates are 27 to 29 November 2026. Numbers marked **[to fill]** come from runs not yet made when this was written; every other number is from a run or a test named in `DRILLS.md`, `EVIDENCE.md` or `EVALUATION_REPORT.md`.*

## Situation

After Phase B the landscape ran, recovered and could be traced. It still behaved like a demo for one customer: one policy for everybody, one tenant's data in the tests, and a deploy button that went straight to 100 % of traffic. A forward-deployed engineer's real job starts here: make it fit a customer's rules, prove customers cannot see or starve each other, and ship changes so that a bad one is undone by the pipeline, not by a person.

## What was built

- **Customers as configuration.** A customer is a file laid over the base policy: currencies, adjustment limits, roles, approver role, how many different approvers (Acme one, Globex two), the window to decide (24 h and 48 h) and extra masking. Two simulated customers ship with discovery records that trace every setting to an answer, and one service is tested with both through six journeys.
- **Tenant isolation, tested.** 24 tenants through one service: no read or approval crosses a tenant; a noisy tenant is refused (retryable) while a quiet one is served, tested with an async gate rather than sleeps.
- **Promotion with a canary and automatic rollback.** A `promote` workflow: a no-traffic revision on its own tag URL, a 10 % canary, the 14-step scenario against the candidate, 100 %, the scenario again; a failed gate restores the previous revision. A `break` switch ships a deliberately broken candidate to watch it work.
- **Adversarial tests.** 45 cases where the *model* is the attacker (hostile drafts: negative, NaN, wrong currency, wrong settlement, over the limit) and where records and documents carry instructions; plus hostile callers.
- **Measurement and one optimisation.** Per-agent model calls, tokens and seconds; the intent of a plain request is read by rules, so the model is not asked.
- **Answers from the customer's documents.** A new question type: "What is the write-off limit?" is answered from the customer's own synthetic documents, cites the passage, and cannot state a figure the passage lacks. A test compares each customer's documents with the enforced policy.
- **Metrics on the model's share of the work.** One log line per answer, turned by Terraform into a degraded-answers counter and a token distribution.

## What was measured

| Question | Result |
|---|---|
| Tests | 176 pass (from 107 at the start of Phase C), including 45 adversarial and 24-tenant isolation |
| Model calls per request, intent by rules vs model (simulated model, exact) | 2 → 1 for every request type; tokens 12 to 23 % fewer |
| The same on the live model, Gemini free tier, 3 runs | **[to fill: calls, tokens, seconds before and after]** |
| Promotion, good candidate | **[to fill: revisions, gate results, minutes from start to 100 %]** |
| Promotion, deliberately broken candidate | **[to fill: which gate failed, seconds from the failed gate to 100 % back on the previous revision]** |

## What went wrong, and what each failure taught

1. **A new pipeline failed three times before it worked, and each failure was informative.** An output wired to the wrong step left the previous revision unknown (the traffic split had `=90`); then the gate failed on step 1. The tag URL and the token audience, the part I had flagged as unverified, worked the first time; what failed was a finite resource.
2. **A finite resource, again.** The O2C stock tops up once per UTC day by design; the day's stock was already spent by earlier runs, so a second restock the same day added nothing. I had given a command that could not work. The rollback did run correctly each time, which is its own evidence.
3. **The adversarial tests found a real gap on the first run.** `ignore   the above instructions` (extra spaces, the word "the") passed the firewall. The patterns were rewritten to tolerate whitespace and filler words, and the case stays in the suite.
4. **My first tests were wrong, not the system.** An empty question is a validation error (HTTP 400), not a refusal; a request with no record id and no policy words is unsupported by design. Writing the test forced me to state the contract.
5. **Conformance rules caught design shortcuts.** Per-request governance by overriding a public method, and a protected hook called from outside, both failed the framework's conformance kit and were redesigned (a context manager, a public method) rather than waived.

## What changed because of it

Policies are per tenant; the firewall tolerates whitespace and filler; the intent step costs no model call when the request is plain; a policy question is answered from documents that CI proves agree with the rules; a candidate revision is gated before it takes traffic and rolled back automatically when it fails; and the model's share of the work is a metric.

## What remains, and what this does not show

- Two customers are simulated, and on the live cloud only one is real: the other services serve one tenant per deployment (gap G-10). Isolation is proven on stand-ins.
- The canary gets the scenario's traffic and almost no real traffic, so the gate, not live error rates, is what catches a bad candidate. `ops deploy` still bypasses it.
- Document search is lexical over a handful of passages; a paraphrase sharing no word finds nothing (the answer is then NOT_FOUND, never invented).
- Per-tenant capacity is per instance. One author, one project.

## Where to look

`docs/customers/`, `genai-assistant-service/tests/test_customers.py`, `test_isolation.py`, `test_adversarial.py`, `test_intent_by_rules.py`, `test_documents.py`; `.github/workflows/promote.yml` and Drill 6 in `docs/DRILLS.md`; `landscape/measure.py`; `landscape/observability/`; `docs/RUNBOOK.md` (sections on measurement, documents, promotion and the log-based metrics).
