# Customers (simulated)

Two fictional customers of the finance GenAI assistant, each with a discovery record and a solution design, and each one a configuration file the service reads (`genai-assistant-service/policies/customers/<tenant>.yaml`). **Both are invented for this portfolio project: the companies, people, volumes and answers are simulated. What is real is the method, the configuration, and the tests that prove the same code serves both.**

| | Acme Retail | Globex Logistics |
|---|---|---|
| Record | [ACME_RETAIL.md](ACME_RETAIL.md) | [GLOBEX_LOGISTICS.md](GLOBEX_LOGISTICS.md) |
| Tenant file | `policies/customers/acme.yaml` | `policies/customers/globex.yaml` |
| Currency | EUR | USD |
| Write-off / refund limit | 250.00 / 1,000.00 | 1,000.00 / 5,000.00 |
| Roles | investigator, finance-approver | analyst, controller |
| Approvers per adjustment | 1 (not the requester) | 2 different controllers (neither the requester) |
| Window to decide | 24 hours | 48 hours |
| Masked in what the assistant says | IBAN, card, e-mail | those, plus US phone numbers and bank account numbers |

## The method, in the order a forward-deployed engineer works

1. **Discovery.** Ask what the business does today, where it hurts, who may approve what, what the auditors and the data-protection officer require. Write the answers down, with the person who gave them.
2. **Map every answer to a decision.** Each line of a customer's configuration traces to a discovery answer (the "Traceability" table in each record). If a setting has no answer behind it, it does not belong in the file.
3. **Configure what can be configured; build only what cannot.** Limits, currency, roles, approvers, windows and masks are configuration. The one thing Globex needed that did not exist (two approvers in turn) was built once, tested, and is available to every customer.
4. **Prove it with the same code.** The tests send both customers through one service on the same stand-ins (`tests/test_customers.py`): the same request is refused for Acme and offered to Globex, roles are not interchangeable, Globex posts nothing until the second controller approves, an approval waits through a restart, and each customer has its own window.
5. **Roll out in steps, with a way back** (the rollout plan in each record).

## What this does not show

- Real customers, real volumes or real regulation. The stand-ins' data is synthetic and the discovery answers are written by one author.
- A second customer on the live cloud services. The assistant is configured per customer; reconciliation serves one tenant per deployment (`RECON_TENANT`), and the ledger's demonstration accounts are seeded for Acme only, so a Globex run against the real cloud would need those services made multi-tenant. That is stated in the solution design of each record, not hidden.
