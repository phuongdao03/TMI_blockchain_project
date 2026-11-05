# Finance Admin Approval Workflow

## Current scope

The backend supports manual withdrawal review, operator-recorded identity and
bank verification, finance settings, supported-bank updates, payOS payout
dispatch, and an internal ledger/reservation reconciliation summary. Payout
execution is separately permissioned and gated. Affiliate commission review
routes and backend affiliate endpoints remain pending. User/admin withdrawal
UI exists; affiliate UI calls currently lack backend endpoints.

## Permission matrix

| Permission | Current endpoint use |
|---|---|
| finance.read | Admin withdrawal list/detail and internal reconciliation |
| finance.withdrawals.approve | Approve or reject withdrawal |
| finance.payouts.execute | Queue and dispatch an approved payout |
| finance.identity.verify | Record identity review and verify a withdrawal bank |
| finance.settings.manage | Read/update withdrawal and payout settings |
| finance.banks.manage | Add/update an enabled or disabled bank BIN |
| affiliate.read | Seeded capability only; no backend route uses it |
| affiliate.commissions.approve | Seeded capability only; no commission route |
| affiliate.rules.manage | Seeded capability only; no affiliate rule route |

Capability checks are enforced by the API, not just by navigation. Confirm
permission assignments in the authorization system before exposing finance
actions. Mutating endpoints use the application's CSRF-protected session
dependency.

## Withdrawal and payout procedure

1. Review the request detail: owner, amount, fee/net amount, bank snapshot,
   identity evidence, available/reserved balances, and current state.
2. Verify identity and destination evidence through the authorized review
   actions. These store operator references; they do not call KYC or bank
   validation services.
3. Confirm the requester is not the approving actor. If the configured
   two-person threshold applies, obtain the second distinct approval.
4. Approve or reject. Rejection needs a reason and releases the reserve once.
   Approval changes the request to APPROVED but does not submit a payout.
5. A separately authorized finance operator invokes
   POST /api/v1/admin/withdrawals/{id}/payout. The service rechecks
   environment/provider/credential/database gates, creates one payout attempt,
   and dispatches the worker.
6. Check the request state and audit/event history. The worker submits the
   snapshotted destination and net amount, then polls known provider IDs.
   Unknown outcomes retain the reserve. If no provider ID was received, resolve
   through the provider before any retry or ledger action.

Finance detail includes the full bank account number and name. Restrict it to
trusted finance operators; do not copy sensitive data into tickets or routine
logs.

## Audit and notification evidence

Withdrawal actions write audit entries, immutable WithdrawalEvent rows, and
in-app notifications. Payout attempts store a stable reference/idempotency key,
provider ID when known, state, and redacted response/error data. There is no
provider-result detail API or payout callback yet.

## Commission review target (pending)

The future commission review must display source payment, attribution,
calculation/rule snapshot, hold completion, refund state, and fraud signals.
A separate operator approves before one finance-ledger credit. The beneficiary
cannot approve their own commission. Preserve rejected/reversed history and use
reasoned source records.