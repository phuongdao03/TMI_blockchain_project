# Financial Reconciliation Runbook

## Scope and limits

The read-only endpoint checks internal finance journals and open withdrawal
reserves. It does not query payOS. A Celery task polls payout IDs known to the
worker, but the endpoint does not report provider status or payout attempts.

Endpoint: GET /api/v1/admin/payouts/reconciliation (finance.read). It returns:

- checked_journals
- unbalanced_journals and up to 100 affected journal IDs
- checked_reserved_accounts
- reserved_balance_mismatches with user ID and ledger/request reserve totals

Open reserve states are PENDING_REVIEW, APPROVED, QUEUED, PROCESSING, and
RECONCILIATION_REQUIRED.

## Internal reconciliation procedure

1. Run the endpoint with a finance operator identity after schema changes and
   at the approved finance operations cadence.
2. Save timestamp, request ID, counts, and affected internal IDs in the
   restricted finance incident record. Do not copy full bank account numbers.
3. If an unbalanced journal or reserve mismatch appears, disable
   WALLET_WITHDRAWAL_ENABLED and the database withdrawal_enabled setting.
   Also disable PAYOUT_LIVE_ENABLED and database payout_live_enabled to stop
   dispatch and worker calls. Escalate to finance and engineering owners.
4. Inspect append-only finance_journals, finance_entries, withdrawal_requests,
   withdrawal_events, and payout_attempts. Trace source references,
   idempotency keys, provider IDs, event history, and audit records.
5. Do not edit/delete finance history, manually adjust balances, retry an
   uncertain payout, or release a reserve based on an unverified result.
   Correct discrepancies only through an approved compensating journal with
   reason and durable audit evidence.
6. Re-run the endpoint after correction and obtain independent review before
   reopening requests or payout dispatch.

## Provider outcome reconciliation

Celery Beat runs the payout reconciliation task every 60 seconds. It queries
PROCESSING or UNKNOWN attempts only when a provider payout ID is available.
Attempts left in SENDING for over five minutes are changed to UNKNOWN /
RECONCILIATION_REQUIRED; this does not release the reserve.

For a known provider ID, compare the provider response to the attempt and
withdrawal: stable reference, amount, destination BIN and masked suffix,
provider ID, terminal state, fee, and settlement date. Record the evidence and
reviewer in a restricted finance incident record.

If the create response was ambiguous before a provider ID was saved, automated
polling cannot resolve it. Search the provider dashboard/support using the
stable PayoutAttempt reference ID. Keep the reserve, and do not retry create or
release funds until the provider confirms the result. The current app has no
operator endpoint for recording this manual resolution; escalation and a
reviewed corrective implementation are required.

## Queue dispatch recovery

The payout API persists a QUEUED attempt and then directly sends a Celery task.
The periodic task reconciles provider outcomes but does not re-submit queued
attempts. If broker dispatch fails, keep the row and reserve intact, disable new
payout dispatch, and have engineering review a safe, idempotent re-dispatch
path. Do not invoke the provider manually outside the controlled recovery.