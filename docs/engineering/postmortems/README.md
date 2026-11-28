# Post-incident reviews

Blameless reviews of failures found while building and operating the landscape: what happened, why the system allowed it, what we learned, what changed. None affected a user (the landscape is synthetic and has none); each cost real time or showed a real design gap, and several were caused by my own earlier changes, which the reviews say plainly. Dates are those of the work in November 2026; where the exact day was not recorded the review says so, and times are given only where a log recorded them.

Template: [`TEMPLATE.md`](TEMPLATE.md). Severity here is by what it would mean in production: **SEV-2** a customer-visible wrong or blocked outcome, **SEV-3** a degraded or blocked internal process, **SEV-4** a near miss or a test that failed for its own reasons.

| # | Review | Severity | Cause class |
|---|---|---|---|
| [0001](0001-ledger-account-drained-by-test-payment.md) | A seeded ledger account drained by the test payment | SEV-3 | test design, finite resource |
| [0002](0002-o2c-stock-exhausted.md) | O2C stock exhausted, scenario step 1 failing | SEV-3 | test design, finite resource |
| [0003](0003-open-items-piled-up.md) | Open items piled up; reconciliation stopped seeing the current settlement | SEV-2 | defect I introduced |
| [0004](0004-wrong-settlement-proposals-refused.md) | A correct refusal of a wrong-settlement proposal, three times | SEV-4 | prompt and data ambiguity |
| [0005](0005-vulnerability-scan-took-three-attempts.md) | Vulnerability scan finding took three attempts to fix | SEV-4 | misdiagnosis |
| [0006](0006-scorer-passed-trials-the-model-never-answered.md) | Scorer passed trials the model never answered | SEV-3 | evaluation defect |
| [0007](0007-first-backup-restore-failed.md) | First backup restore failed | SEV-4 | drill design, least privilege |
| [0008](0008-promotion-pipeline-first-runs-failed.md) | The promotion pipeline's first runs failed | SEV-4 | defect, finite resource |
| [0009](0009-cloud-shell-network-failures.md) | Cloud Shell could not push images or apply Terraform | SEV-4 | environment |
| [0010](0010-firewall-pattern-gap.md) | The prompt-injection firewall missed `ignore   the above instructions` | SEV-3 | gap found before use |
