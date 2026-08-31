# Spec: Listed-price billing and PayOS checkout

## Objective

Replace operator-entered amounts with a versioned price catalog and automatic
billing:

`APPROVED -> fee obligation -> user notified -> PayOS checkout -> verified payment -> blockchain/certificate queue`

The admin payment area becomes a finance workspace for cash flow,
transactions, reconciliation, refunds and exceptions. It is not the normal
place where staff manually decide a dossier fee.

The four roles remain `VIEWER`, `USER`, `MODERATOR`, and `SUPER_ADMIN`.
Capabilities continue to use granular permissions.

## Assumptions to validate

1. Each active dossier type has one published standard VND fee. The model may
   support service packages later without requiring them in the first release.
2. Approval locks the applicable price and price version; later catalog changes
   never alter an existing obligation.
3. Normal pricing is automatic. Finance can waive or adjust only through a
   reason-required, audited exception.
4. Payment terms default to seven days and are independent from the lifetime of
   an individual PayOS checkout link.
5. Email is required in addition to the existing in-app notification.

## Domain language

- **Price Catalog**: versioned published fees by dossier type and optional
  service package.
- **Fee Obligation**: immutable commercial snapshot for an approved dossier,
  including price, description, tax treatment, currency and due date.
- **Checkout Session**: one short-lived PayOS link/QR for an unpaid obligation.
  It is not the debt itself and may be safely regenerated.
- **Payment Transaction**: provider-confirmed money movement associated with a
  checkout session.
- **Reconciliation Case**: persisted discrepancy between internal records and
  PayOS requiring automated or human resolution.
- **Gross Collected**: successful incoming transactions before refunds/fees.
- **Net Collected**: gross collected minus successful refunds and recorded
  provider fees. This is not automatically accounting revenue.

## Pricing rules

- Catalog entries are versioned and append-only after publication.
- Required fields: dossier type, service code, name, amount, currency,
  effective interval, tax mode, status and version.
- Only one published entry may be effective for a dossier type/service/time.
- Publishing requires `pricing.manage`, recent authentication, confirmation,
  reason and audit evidence.
- Approval fails safely and alerts operations when no unique price exists. The
  system never silently uses a fallback amount.
- Price changes apply only to later approvals.
- A waiver/adjustment creates a revision referencing the original; financial
  history is never edited in place.

## State models

### Fee obligation

`OPEN -> PAID`

`OPEN -> OVERDUE -> PAID`

`OPEN|OVERDUE -> WAIVED`

`OPEN|OVERDUE -> CANCELLED` only when approval is formally withdrawn. Terminal
financial records are retained.

### Checkout session

`PENDING -> PROCESSING -> PAID`

`PENDING|PROCESSING -> EXPIRED|CANCELLED|FAILED`

Session expiry never erases the obligation. An unpaid, non-overdue obligation
may create another session.

### Dossier

`APPROVED -> PAYMENT_DUE -> PAID -> BLOCKCHAIN_PENDING`

Only a verified PayOS webhook or provider reconciliation confirms payment.
Browser return parameters are presentation-only.

## Lifecycle

1. Approval completes the dossier transaction.
2. Billing resolves exactly one effective catalog entry and atomically creates
   an obligation with an idempotency key derived from dossier/version.
3. The owner receives in-app and email notifications. Both point to the durable
   obligation page, never directly to an expiring PayOS URL.
4. Account home and dossier detail show exact fee, due date and one
   `Thanh toán ngay` action.
5. That action reuses a valid checkout or creates a PayOS session with a
   30-minute `expiredAt`.
6. An expired session offers `Tạo mã thanh toán mới`; creation first checks
   PayOS to avoid replacing a payment whose webhook is delayed.
7. A signature-valid, amount-matched webhook records a transaction, settles the
   obligation once, notifies the user and enqueues blockchain/certificate once.
8. Reminder jobs notify at configured milestones without duplication.

## API contract

All routes use `/api/v1` and the existing response envelope.

### User billing

- `GET /billing/obligations?page=&pageSize=&status=`
- `GET /billing/obligations/{obligationId}`
- `POST /billing/obligations/{obligationId}/checkout-sessions`
  - CSRF protected and idempotent.
  - Reuses a usable session or creates a new PayOS session.
- `GET /payment-orders/{sessionId}` remains during migration.

The session response includes `checkoutUrl`, `qrPayload`, `expiresAt` and
provider status. It never exposes PayOS credentials.

### Pricing administration

- `GET /admin/pricing/catalog`
- `POST /admin/pricing/catalog/versions`
- `POST /admin/pricing/catalog/versions/{versionId}/publish`
- `POST /admin/billing/obligations/{obligationId}/adjustments`

### Finance administration

- `GET /admin/finance/summary?from=&to=`
- `GET /admin/finance/transactions?page=&pageSize=&status=&from=&to=&query=`
- `GET /admin/finance/transactions/{transactionId}`
- `GET /admin/finance/reconciliation?page=&pageSize=&status=`
- `POST /admin/finance/reconciliation/{caseId}/resolve`
- Refund remains unavailable until provider support, approval policy and
  accounting treatment are explicitly implemented.

## User experience

### Account home

- A high-priority payment card appears automatically after approval.
- It shows dossier, listed fee, due date and one primary action.
- Notification center deep-links to the obligation.
- Email carries the same durable link, never a QR that can silently expire.

### Billing page

- Timeline: approved, fee issued, payment status, blockchain/certificate next.
- Mobile summary keeps amount and action above the fold.
- QR renders only for a live session with countdown and exact expiry;
  `checkoutUrl` remains the accessible alternative.
- Expiry is recoverable in one tap without support.
- Loading, provider outage, delayed webhook, expired, paid and overdue states
  have distinct copy and next actions.

### Finance workspace

- Navigation becomes `Tài chính`; `Yêu cầu thanh toán` is removed as the
  primary admin destination.
- Overview separates gross collected, refunds, fees, net collected, pending
  obligations, overdue value, failed sessions and reconciliation exceptions.
- Charts show collected cash and statuses; no fake revenue label.
- Server-paginated transactions filter by date, status, dossier, user, order
  code and amount.
- Detail shows obligation, PayOS identifiers, webhook evidence,
  reconciliation state and audit trail.
- Pricing is a separate configuration subpage, not mixed into transactions.

## Data and migration

Required concepts, reusing existing tables where possible:

- `price_catalog_versions`
- `price_catalog_entries`
- `fee_obligations`
- existing `payment_orders` becomes checkout sessions linked to obligations
- existing append-only `payment_events` remains provider evidence
- `payment_transactions`
- `reconciliation_cases` and immutable resolution history

Existing orders are backfilled into obligations without changing provider IDs
or paid state. Migration remains reversible before legacy writes are retired.

## Security and audit

- Deny-by-default permissions: `pricing.read`, `pricing.manage`,
  `payments.read`, `payments.reconcile`, `payments.adjust`, `payments.export`.
- Price resolves server-side; clients never choose the payable value.
- PayOS responses/webhooks are untrusted and signature checked.
- Publishing, adjustment, waiver, session creation, expiry, payment,
  reconciliation, export and configuration changes are audited.
- No secret, sensitive raw webhook or long-lived signed URL is logged.

## Success criteria

- Approval creates exactly one correctly priced obligation and notification.
- No normal admin action manually enters a dossier amount.
- A user returning days later can generate a fresh PayOS checkout and pay.
- Duplicate clicks/webhooks/jobs never duplicate debt or settlement.
- Finance totals reconcile to persisted transactions, refunds and fees.
- User, finance and pricing permissions are enforced server-side.
- Mobile at 320/360/390px has no overlap or horizontal overflow; the primary
  action remains reachable above bottom navigation.
- Backend/frontend/RBAC tests, migration, lint, typecheck and build pass before
  the legacy write path is removed.

## Sources

- payOS Merchant API and `expiredAt`: https://payos.vn/docs/api/
- payOS Checkout lifecycle: https://payos.vn/docs/checkout/how-checkout-works/
- payOS webhook: https://payos.vn/docs/du-lieu-tra-ve/webhook/

## Open decisions

- Initial published fee for each dossier type.
- Whether prices include tax and whether invoices are required.
- Default payment term (proposed: seven days) and reminder schedule.
- Whether adjustments require one or two authorized approvers.
