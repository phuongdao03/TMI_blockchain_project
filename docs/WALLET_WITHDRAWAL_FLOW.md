# Wallet Withdrawal Flow

## Status

Bank-account management, withdrawal reservation/review, a separate payOS
payout adapter, and worker polling are implemented. All live-money gates
default closed. A withdrawal is paid only after approval and a separate
permission-gated payout dispatch; approval alone never sends money.

## Eligibility and request creation

The user chooses an active bank account and submits an integer VND amount with
an Idempotency-Key. In one transaction the backend:

1. Confirms environment WALLET_WITHDRAWAL_ENABLED and database
   withdrawal_enabled are both true.
2. Requires positive daily amount/count limits, an active email-verified user,
   verified financial identity, an active bank account, and an enabled bank BIN.
3. Enforces minimum/maximum, daily count/amount limits, and fee mode
   (NONE, FIXED, or BPS).
4. Checks only the user's COMMISSION_AVAILABLE finance account. The prepaid
   service wallet is never consulted.
5. Creates PENDING_REVIEW, snapshots encrypted bank details, and transfers
   the requested amount into COMMISSION_RESERVED.

The same key and same payload returns the existing request. Reusing a key for a
different amount or bank account conflicts.

## Implemented state transitions

    PENDING_REVIEW -- approve --> APPROVED
           |                        | finance.payouts.execute
           |                        v
           |                     QUEUED --> PROCESSING
           |                                  |-- SUCCEEDED (settle reserve)
           |                                  |-- FAILED (release reserve)
           |                                  '-- RECONCILIATION_REQUIRED
           |                                       (retain reserve)
           |-- reject --> REJECTED (release reserve)
           '-- cancel --> CANCELLED (release reserve)

An unknown payOS outcome retains the reserve and must not trigger another create
call. Known provider payout IDs are polled by Celery. If the create result is
ambiguous and no payout ID was received, the system marks the request
RECONCILIATION_REQUIRED; operator/provider resolution is required.

## Review and payout requirements

- Approval/rejection requires finance.withdrawals.approve; the requesting
  user cannot approve or reject their own request.
- A configured two-person threshold requires two distinct approvers. The first
  approval leaves the request in PENDING_REVIEW.
- Before approval and again before submission, identity must remain verified
  and the selected bank account must be active and operator-verified.
- Payout submission requires finance.payouts.execute, the environment payout
  gate, provider selection, credentials, and database payout setting.
- Rejection requires a reason and releases the reserve once. User cancellation
  is permitted only while PENDING_REVIEW.
- Decisions, state events, audit records, and notifications are written by the
  service in the database transaction.

Identity and bank checks are operator-recorded evidence references, not an
integrated identity or destination-validation provider.

## Bank account handling

Bank BINs must exist in the enabled supported_banks catalogue. Account number
and name are encrypted with the configured PII encryption key. User responses
contain a masked number; finance detail contains full bank data and requires
finance permission. Existing accounts are disabled rather than deleted. Each
withdrawal retains the bank snapshot from request time.

## Release gates

Withdrawal and payout flags, database settings, provider mode, and credentials
remain closed/unconfigured by default. A production commission-credit source,
approved legal/compliance policy, verified bank catalogue and identity process,
operator permissions, tested provider outcome handling, and reconciliation must
exist before activation.

See [Admin Approval Workflow](ADMIN_APPROVAL_WORKFLOW.md),
[payOS Payout Integration](PAYOS_PAYOUT_INTEGRATION.md), and
[Deployment and Rollback](runbooks/wallet-affiliate-deployment-and-rollback.md).
