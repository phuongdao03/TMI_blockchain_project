# payOS merchant readiness

## Before deployment

1. Complete payOS identity or business verification and link the settlement bank.
2. Create the TMI payment channel and copy Client ID, API Key and Checksum Key
   directly into the deployment secret manager. Never put them in Git or CI logs.
3. Deploy the backend behind HTTPS, then register
   `https://<api-host>/api/v1/webhooks/payments/payos` in the payOS channel.
4. Confirm that the sample webhook receives HTTP 2xx only after signature checking.
5. Set HTTPS return and cancellation URLs to the frontend payment result routes.

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
