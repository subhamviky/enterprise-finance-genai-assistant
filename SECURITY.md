# Security

This is a **reference implementation, not a production service**: it runs on synthetic data, and
nothing in it may be pointed at real customer or payment data.

## Reporting a vulnerability

Please report a suspected vulnerability privately through GitHub's
[security advisories](https://github.com/subhamviky/enterprise-finance-genai-assistant/security/advisories/new),
not in a public issue. You will get an answer within a week.

## What the design guarantees, and where it is tested

| Guarantee | Where |
|---|---|
| Default-deny: every service is private behind Cloud Run IAM; the caller's Google ID token is verified, then its tenant and roles come from the deployment's grants, never from the request | `routers/identity.py`, `tests/test_api.py` |
| A model never moves money: an adjustment needs a valid proposal (checked by policy, not by the model) and the approval of a second person with the approver role | `services/policy.py`, `workflow/investigation_workflow.py`, `tests/test_failure_matrix.py` |
| Each adjustment posts once: idempotency keys end to end, a replayed or concurrent approval is refused | `agents/execution_agent.py`, `tests/test_failure_matrix.py` |
| Answers are grounded: every citation is a record that was read; unsupported claims are refused | `agents/investigator_agent.py`, `evals/golden.json` |
| Prompt injection, in the request or in a retrieved record, causes no action | `policies/governance.yaml`, `evals/redteam.json`, `tests/test_safety.py` |
| No secrets in code, state or logs: the Gemini key is a Secret Manager secret; IBANs, card numbers and e-mail addresses are redacted on the way out | `policies/governance.yaml`, `evals/redteam.json` |
| Least privilege: each agent may call only its listed tools; tool arguments are validated at execution | `policies/governance.yaml`, `tools/catalog.py` |
