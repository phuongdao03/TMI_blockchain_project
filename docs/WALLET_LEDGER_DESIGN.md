# Wallet and Finance Ledger Design

## Status

The repository has two separate ledgers. wallet_journals supports prepaid
service spending. finance_journals accounts for affiliate commission liabilities,
withdrawal reserves/releases, and payout settlement. The payout worker can
settle a recorded successful provider result; affiliate commission generation
and credit sources are not implemented.

## Prepaid service wallet

Wallet.balance_minor is an integer VND balance used for service purchases.
WalletLedger.post updates it under a row lock, rejects a negative result, and
adds an immutable journal row with equal/opposite wallet_delta and
counter_delta. Idempotency and source references are unique. Migration
0127_internal_wallet installs triggers that reject journal updates/deletes.

This is a prepaid service balance. It is not eligible for withdrawal and must
not be merged with affiliate commission amounts.

## Finance accounts and entries

FinanceAccount identifies an owner or platform account. The account chart is
constrained to VND and includes:

| Account | Owner | Use |
|---|---|---|
| COMMISSION_AVAILABLE | User | Commission eligible for a withdrawal request |
| COMMISSION_RESERVED | User | Commission reserved by an open withdrawal |
| COMMISSION_EXPENSE | Platform | Counter account for commission credit/reversal |
| PAYOUT_SETTLEMENT | Platform | Counter account for settled net payout |
| WITHDRAWAL_FEE_REVENUE | Platform | Counter account for withdrawal fees |

FinanceLedger.transfer locks both accounts in stable ID order and writes one
FinanceJournal plus two signed FinanceEntry rows. Source is negative and
destination positive. Supported transaction pairs are COMMISSION_CREDIT,
WITHDRAWAL_RESERVE, WITHDRAWAL_RELEASE, PAYOUT_SETTLEMENT, WITHDRAWAL_FEE, and
COMMISSION_REVERSAL. Available and reserved balances are sums of entries, not
cached balances.

Journal idempotency keys and source references are unique. Replays must match
transaction type, reference, accounts, and amount. Accounts, journals, and
entries are append-only. The schema checks individual entries; service logic
and reconciliation check exactly two entries whose sum is zero.

## Withdrawal and payout transaction boundaries

A withdrawal request and transfer from COMMISSION_AVAILABLE to
COMMISSION_RESERVED are created in one transaction. Rejection or cancellation
appends one WITHDRAWAL_RELEASE pair. Approval records a decision only. A
separate finance.payouts.execute action queues one PayoutAttempt with a stable
provider reference and idempotency key. The worker marks it SENDING before the
provider call.

After a recorded provider success, the service transfers the net amount from
COMMISSION_RESERVED to PAYOUT_SETTLEMENT and the fee, if any, to
WITHDRAWAL_FEE_REVENUE. A terminal failure releases the request reserve.
Ambiguous outcomes keep it reserved and move the withdrawal to
RECONCILIATION_REQUIRED. The PayoutAttempt schema and migration allow SENDING.
An unknown result without provider ID requires manual provider resolution;
there is no public app endpoint to record that resolution.

No current affiliate service posts COMMISSION_CREDIT. Tests may seed funds
through the ledger service; that is not a production commission source.

## Reconciliation

WalletWithdrawalService.reconciliation_summary checks journal pair count/sum
and compares each user's reserved ledger total to open withdrawal requests.
GET /api/v1/admin/payouts/reconciliation requires finance.read. It is internal
ledger reconciliation, not a provider report. Celery polls known provider IDs
separately. See FINANCIAL_RECONCILIATION_RUNBOOK.md.

## Source files

- backend/app/modules/wallet/models.py
- backend/app/modules/wallet/service.py
- backend/app/modules/wallet/withdrawal_service.py
- backend/app/modules/wallet/payout_gateway.py
- backend/app/workers/payout_tasks.py
- backend/alembic/versions/0127_internal_wallet.py
- backend/alembic/versions/0153_finance_ledger.py
- backend/alembic/versions/0154_wallet_withdrawals.py