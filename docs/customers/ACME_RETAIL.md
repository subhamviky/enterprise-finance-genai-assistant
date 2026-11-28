# Acme Retail: discovery and solution design

*Simulated customer. Every name, number and answer below is invented for this portfolio project.*

## 1. Who they are

A mid-sized European retailer: about 400 stores, one finance shared-service centre, euros only. Customers pay by card and bank transfer; transfers are matched to open receivables by an overnight job, and what does not match lands on a queue worked by three accounts-receivable analysts.

## 2. Discovery: what we asked, and what they said (simulated)

| # | Question | Answer (given by) |
|---|---|---|
| 1 | What are you trying to improve? | The unmatched queue: about 60 lines a day, most of them a few euros short. Each takes 10 to 15 minutes to explain and decide. (AR team lead) |
| 2 | Who may write money off, and how much? | An analyst proposes; a finance approver decides. Up to 250 EUR for a write-off, up to 1,000 EUR for a refund. Above that goes to the controller outside this tool. (Head of finance operations) |
| 3 | Who approves? | One finance approver other than the person who asked. Two people is the rule for money leaving the books. (Head of finance operations) |
| 4 | What happens to a proposal nobody answers? | It must not hang for ever. A day is enough: the analyst asks again the next morning. (AR team lead) |
| 5 | What currencies? | Euro only; the one-off non-euro payment is handled by treasury by hand. (Treasury) |
| 6 | What personal data may appear in what the assistant says? | IBANs, card numbers and e-mail addresses must never be repeated back; our DPO is strict about it. (Data protection officer) |
| 7 | What must be auditable? | Who proposed, who approved, which ledger entry, and that nothing was posted without approval. (Internal audit) |
| 8 | What would make you stop using it? | One posting on the wrong settlement, or one it could not explain afterwards. (Head of finance operations) |

## 3. Current state

Analysts open three screens (the bank statement line, the ledger, the order system), compare amounts by eye, write a note, and raise a write-off request in the ledger tool. Approvals are by e-mail. The note is free text. Wrong-settlement postings happen a few times a year and are found at month end.

## 4. Solution design

The assistant investigates a line (reads the exception, the line, the settlement, its events and audit findings, and cites each), proposes a write-off or refund, and waits for an approver. After approval it posts to the settlement ledger once, reads the entry back, and asks reconciliation to close the exception.

**Traceability: every setting to an answer**

| Setting in `acme.yaml` | Value | Answer |
|---|---|---|
| `currencies` | EUR | 5 |
| `adjustments.WRITE_OFF / REFUND` | 250.00 / 1,000.00 | 2 |
| `approval.approver_role`, `four_eyes` | finance-approver, true | 2, 3 |
| `approval.approvals_required` | 1 | 3 |
| `approval.expires_after_hours` | 24 | 4 |
| redaction (the base masks) | IBAN, card, e-mail | 6 |
| not a setting: citation of every record read, posting once, read-back, exception closed | built | 7 |
| not a setting: a proposal on the wrong settlement is refused (it must be a candidate of the line and the exact difference; ambiguity asks which) | built | 8 |

## 5. Risks and what answers them

| Risk | Answer |
|---|---|
| The model drafts a write-off on the wrong settlement | policy check against the bank line and the candidate list; ambiguity is refused and asks; proven in CI and found live once |
| An approver approves what they did not read | the approval record carries the cited records; the proposal states amount, settlement and reason |
| A proposal goes stale | expires after 24 hours; an expired approval cannot be approved |
| The model is down | the system answers with the verified facts and says it is degraded; nothing is posted |
| Over-trust | the assistant never posts without a second person; the limit is policy, not prompt |

## 6. Rollout plan

1. **Shadow (2 weeks):** analysts keep their process; the assistant explains the same lines; compare explanations and amounts. Exit: no explanation contradicted by the ledger.
2. **Propose only (2 weeks):** the assistant drafts, the analyst compares with their own decision, nothing is approved through it.
3. **Approve and post, small lines (4 weeks):** one approver, limit lowered to 50 EUR first. Exit: zero wrong-settlement postings, every posting has its read-back.
4. **Full limits.** Roll back by switching the tenant file to propose-only (limit 0); nothing else changes.

Success measures: minutes per unmatched line; share of lines closed first time; wrong-settlement postings (target zero); proposals expired unanswered.

## 7. Open questions (simulated)

Whether non-euro one-offs should be proposed and refused with a reason, or not proposed at all; how long to keep approval records (audit says seven years; storage is cheap).
