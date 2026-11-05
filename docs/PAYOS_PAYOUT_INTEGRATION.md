# payOS Payout Integration

## Current implementation status

The repository has a separate PayOSPayoutGateway in
backend/app/modules/wallet/payout_gateway.py. It implements single-payout
creation at POST /v1/payouts and lookup by payout ID at
GET /v1/payouts/{payoutId}. It is called only by the gated Celery worker.
It does not implement provider list, estimate-credit, account-balance, or
callback operations.

The admin API requires finance.payouts.execute to queue an already-approved
withdrawal and dispatch process_queued_payouts. The request is not paid by
the approval endpoint. Live payouts remain disabled by environment and database
defaults, with provider set to disabled and credentials absent unless supplied
through the deployment secret store.

## Separate provider configuration

- PAYOS_PAYOUT_PROVIDER=disabled by default
- PAYOS_PAYOUT_CLIENT_ID
- PAYOS_PAYOUT_API_KEY
- PAYOS_PAYOUT_CHECKSUM_KEY
- PAYOS_PAYOUT_BASE_URL=https://api-merchant.payos.vn
- PAYOS_PAYOUT_TIMEOUT_SECONDS
- PAYOUT_LIVE_ENABLED=false by default
- Database finance_settings.payout_live_enabled=false by default

Collection PAYOS_* credentials do not authorize payout calls. Confirm
payout-account enrollment, supported categories/destination banks, limits, fees,
and account eligibility with the provider and merchant account owner.

## Implemented request contract

The adapter posts a single payout with referenceId, integer VND amount,
description, toBin, and toAccountNumber. It sends the stable
x-idempotency-key, x-signature, x-client-id, and x-api-key headers. The payout
HMAC-SHA256 canonicalization is implemented separately from payment-request
signing and URL-encodes sorted key/value pairs.

Official references: [payOS API](https://payos.vn/docs/api/) and
[payOS signature guide](https://payos.vn/docs/tich-hop-webhook/kiem-tra-du-lieu-voi-signature/).

## Execution sequence

1. A finance operator with finance.payouts.execute dispatches only an
   APPROVED withdrawal. The service checks environment/provider/credential
   gates and the database payout flag, then creates one PayoutAttempt with a
   stable provider reference and idempotency key and moves the request to
   QUEUED.
2. The route dispatches process_queued_payouts. The worker locks the request,
   rechecks approval, payout setting, verified identity and verified active
   bank, marks the attempt SENDING and request PROCESSING, then calls payOS
   with the net amount and snapshotted destination.
3. A response with provider ID and a known state is persisted as a redacted
   attempt result. PROCESSING/PENDING remains reserved and is polled.
   Success settles the net amount and fee from the reserve in separate
   idempotent journal entries. A terminal failure releases the reserve once.
4. An ambiguous result becomes UNKNOWN/RECONCILIATION_REQUIRED; the reserve
   stays held. The worker never re-creates a payout just because the create
   response was lost.

Celery Beat polls known payout IDs every 60 seconds. Attempts in
PROCESSING or UNKNOWN with a provider ID are queried by ID. A stale SENDING
attempt older than five minutes is marked unknown. When the result is
ambiguous and no provider payout ID was received, automated lookup cannot
resolve it; operators must reconcile it in the provider dashboard/support
channel before taking any financial action.

The provider adapter currently maps all HTTP errors to an unknown outcome. It
does not distinguish a confirmed non-acceptance response from an ambiguous
response; do not manually retry a create call until the provider reference has
been checked.

## Operational limitations and activation gates

- The queue endpoint writes the attempt before directly dispatching the Celery
  task. The periodic task reconciles outcomes but does not re-submit queued
  attempts. A broker dispatch failure can leave a request queued; a safe
  re-dispatch/recovery process is required before live activation.
- No payout webhook, provider list reconciliation, fee estimate, payout account
  balance check, or dedicated payout-attempt/provider-result route is wired. Admin withdrawal detail exposes events and a saved provider ID.
- Full destination details exist in protected internal storage; never log raw
  account numbers or include them in operator tickets.
- Legal/tax/privacy approval, verified identity and bank evidence processes,
  provider onboarding, independent approvals, monitoring, and rehearsed
  reconciliation/rollback remain required.
- Tests and staging must use a mock/fake gateway and must never create a real
  payout.