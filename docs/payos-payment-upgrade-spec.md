# payOS payment upgrade specification

> Historical implementation baseline. Its applicant-created checkout contract
> is superseded by `admin-issued-payment-flow-spec.md`: Billing V2 creates a
> durable listed-price obligation at approval and creates short-lived PayOS
> checkout sessions only when the user elects to pay. Do not reintroduce the
> legacy write path.

## Objective

Complete the existing payOS payment lifecycle without introducing a parallel
payment implementation. Applicants can create, resume, inspect and cancel an
unpaid checkout. Authorized finance operators can reconcile an order against
payOS. Provider callbacks remain the authoritative asynchronous confirmation.

## Existing architecture to retain

- FastAPI owns provider credentials and calls payOS Merchant API.
- `PaymentGateway` remains the provider boundary; `PayOSGateway` remains its
  production adapter and `MockPaymentGateway` remains local-only.
- `payment_orders` owns internal state and idempotency keys.
- `payment_events` is append-only provider evidence and deduplicates references.
- Browser clients never receive Client ID, API Key or Checksum Key.

## API contract

- `POST /api/v1/dossiers/{dossierId}/payment-orders`
  - Requires authenticated dossier access, CSRF and `Idempotency-Key`.
  - Replays the same internal order for the same key.
- `POST /api/v1/payment-orders/{orderId}/cancel`
  - Requires authenticated dossier access, CSRF and a required reason.
  - Only `PENDING` or `PROCESSING` orders may be cancelled.
  - Calls payOS cancellation using the provider reference, records audit state,
    then returns the dossier to `APPROVED` so a new checkout can be created.
- `POST /api/v1/admin/payment-orders/{orderId}/reconcile`
  - Requires finance permission through the existing server policy.
  - Compares order code, amount, currency and provider state before mutation.
- `POST /api/v1/webhooks/payments/payos`
  - Public endpoint; accepts the exact raw body, verifies payOS HMAC from the
    body, deduplicates the provider reference and rejects amount/order mismatch.

All errors use the existing response envelope. Secrets, bank account details
and unredacted webhook bodies must not enter logs or audit records.

## User experience

- Payment page shows amount, expiry, current status and one dominant action.
- Pending orders expose “Open secure payOS checkout” and a secondary,
  reason-confirmed cancellation action.
- Return/cancel pages never trust query parameters as proof of payment; they
  resolve the internal order and continue polling backend state.
- Mobile targets are at least 44px, no horizontal overflow at 320px, and
  loading/error/stopped states always offer a route back to the dossier.

## Testing

- Gateway: signed create/get/cancel responses and invalid signature rejection.
- Service: idempotent creation, cancellation transition, forbidden/terminal
  cancellation, webhook duplicate and amount mismatch, reconciliation replay.
- API: CSRF/auth boundary, cancellation and finance reconciliation contracts.
- UI/E2E: pending checkout, cancel confirmation, return state and mobile layout.

## Boundaries

- Never perform refunds through the cancellation endpoint.
- Never infer `PAID` from return URL parameters.
- Never expose or log payOS credentials or raw provider payloads.
- Real-money verification remains staging-only and requires the existing cap.

## Success criteria

- Focused payment tests, full backend tests, frontend tests, lint and build pass.
- Duplicate webhook/cancel/reconcile requests cannot create duplicate state.
- Applicant and finance authorization are enforced server-side.
- Deployment runbook identifies merchant setup and webhook verification steps.

## Sources

- payOS Merchant API: https://payos.vn/docs/api/
- payOS Python/FastAPI async SDK guidance: https://payos.vn/docs/sdks/back-end/python/
- payOS payment-request signature rules: https://payos.vn/docs/tich-hop-webhook/kiem-tra-du-lieu-voi-signature/
