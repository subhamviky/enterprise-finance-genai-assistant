# Globex Logistics: discovery and solution design

*Simulated customer. Every name, number and answer below is invented for this portfolio project.*

## 1. Who they are

A US freight carrier: about 2,000 trucks, a controller's office of eight, dollars only. Customers are shippers invoiced on net-30 terms; remittances arrive by ACH and wire, often covering several invoices, often short because of fuel-surcharge disputes and detention fees.

## 2. Discovery: what we asked, and what they said (simulated)

| # | Question | Answer (given by) |
|---|---|---|
| 1 | What are you trying to improve? | Short-paid remittances. About 120 a week; each needs a surcharge or detention explanation and a write-off decision. (Controller) |
| 2 | What size of adjustment do you decide? | Write-offs up to 1,000 USD, refunds (overpaid detention, duplicate wires) up to 5,000 USD. (Controller) |
| 3 | Who approves, and how many? | Anything that moves the books needs two controllers; SOX says the requester cannot be one of them, and no one approves twice. (Controller, internal audit) |
| 4 | What are your roles called? | Analysts propose, controllers approve. Not "investigator" or "finance-approver". (Controller) |
| 5 | How long may an approval wait? | The two controllers are in different time zones: two days. (Controller) |
| 6 | What personal or sensitive data must be masked? | Beyond IBANs, cards and e-mail: phone numbers of dispatchers and the shippers' bank account numbers. (Security lead) |
| 7 | Which currencies? | US dollars only. A Canadian-dollar payment is a different process. (Controller) |
| 8 | What would make you stop using it? | A write-off posted with only one approver, or any posting we cannot show two approvers for. (Internal audit) |

## 3. Current state

The controller's office works a shared spreadsheet of short remittances. A write-off is requested in the ledger tool and approved by two controllers by e-mail; the second approval is often chased for a day. The audit trail is the e-mail thread.

## 4. Solution design

The same assistant, configured for Globex. What differs is only the file `policies/customers/globex.yaml`, except for one capability Globex needed that Acme did not: **several approvers in turn**. It was built once for everyone: an approval records each different approver as it comes (one compare-and-set, so concurrent approvers are both counted), the requester and the wrong role are refused, the same approver twice counts once, and only the last approver needed lets the adjustment post. The receipt lists every approver.

**Traceability: every setting to an answer**

| Setting in `globex.yaml` | Value | Answer |
|---|---|---|
| `currencies` | USD | 7 |
| `adjustments.WRITE_OFF / REFUND` | 1,000.00 / 5,000.00 | 2 |
| `entitlements` (roles) | analyst, controller | 4 |
| `approval.approver_role`, `four_eyes` | controller, true | 3, 4 |
| `approval.approvals_required` | 2 | 3, 8 |
| `approval.expires_after_hours` | 48 | 5 |
| `redaction_add` | US phone, US bank account | 6 |
| built, for every customer: several approvers in turn; the receipt names them | built | 3, 8 |

## 5. Risks and what answers them

| Risk | Answer |
|---|---|
| One controller approves twice, or the requester counts as one | the same approver counts once; the requester is refused; tested |
| The two approvals race | each is recorded by a compare-and-set; one posting only, tested with a second instance and a restart between approvers |
| An approval pending for two days is lost in a release | state is in the store, not the service; proven on the cloud for a single approval and in CI for several |
| An account number is mistaken for an id, or an id for an account number | the account mask excludes anything joined by hyphens or dots, so a settlement UUID or an order number is never masked; tested |
| A currency other than USD | refused for this customer with the reason |

## 6. Rollout plan

1. **Shadow (3 weeks):** the assistant explains short remittances next to the spreadsheet; the controllers mark each explanation right or wrong.
2. **Propose only (3 weeks):** drafts to the analysts, no approvals through the tool.
3. **Two-controller approvals, 250 USD limit (4 weeks):** every posting has two named approvers and a ledger read-back.
4. **Full limits.** Roll back by lowering `adjustments` to zero in the tenant file.

Success measures: minutes per short remittance; share of postings with two approvers and a read-back (target 100 per cent); approvals expired unanswered (a measure of whether 48 hours is the right window).

## 7. Limits of this record, stated plainly

- The assistant layer is proven for Globex on the stand-ins, with both customers through one service. On the real cloud only Acme runs: reconciliation serves one tenant per deployment and the ledger's demonstration accounts are seeded for Acme, so a Globex run on the live services needs those made multi-tenant or seeded.
- All of the above is simulated: the company, the people, the volumes, the answers.
