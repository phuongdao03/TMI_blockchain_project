# payOS merchant readiness

## Before deployment

1. Complete payOS identity or business verification and link the settlement bank.
2. Create the TMI payment channel and copy Client ID, API Key and Checksum Key
   directly into the deployment secret manager. Never put them in Git or CI logs.
3. Deploy the backend behind HTTPS, then register
   `https://<api-host>/api/v1/webhooks/payments/payos` in the payOS channel.
4. Confirm that the sample webhook receives HTTP 2xx only after signature checking.
5. Set HTTPS return and cancellation URLs to the frontend payment result routes.

## Runtime lifecycle checks

1. Create an approved-dossier payment using a unique `Idempotency-Key`; confirm
   the internal order code, amount and currency match the payOS payment link.
2. Complete one payment and confirm only a signature-valid webhook or provider
   reconciliation moves the internal order and dossier to `PAID`.
3. Cancel one unpaid order from the application, provide a reason, and confirm
   payOS reports `CANCELLED` while the dossier returns to `APPROVED`.
4. Finance operators may trigger
   `POST /api/v1/admin/payment-orders/{orderId}/reconcile`; applicants must
   receive 403. Reconciliation must reject mismatched order code, amount or
   currency and must not infer payment from return URL parameters.
5. Inspect the audit trail for `payment.order.created`,
   `payment.order.cancelled`, webhook processing and reconciliation. No secret,
   raw webhook body or bank credential may appear.

## Approved low-value verification

Use staging only. Record the approver and ticket, set
`PAYMENT_REAL_MONEY_TEST_ENABLED=true`, set the cap at or below 100,000 VND and
create an order whose amount is at or below that cap. Restore the flag to `false`
immediately after collecting the provider reference, webhook event and database
state. The flag is rejected when `APP_ENV=production`.

## Release block

Do not enable payOS traffic until merchant verification, bank link, channel,
three secrets, public webhook validation and finance/incident ownership are all
confirmed in ADR-005.
