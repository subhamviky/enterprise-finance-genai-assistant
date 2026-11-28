# Payment matching and short payments

Synthetic document for the demonstration landscape. Not real policy.

## How a bank line is matched

A bank statement line is matched to an open settlement by payer account and amount. A line that matches exactly is reconciled automatically. A line that matches no open settlement becomes an exception and waits for an investigator.

## Short payments

A payer sometimes sends less than the settlement amount, usually because the bank deducted a transfer fee. The difference is a short payment. A short payment is closed with a write-off when it is within the write-off limit of the customer, and with a refund request to the payer when it is over.

## Overpayments

A payer who sends more than the settlement amount is owed the difference. The difference is refunded to the payer, never written off.
