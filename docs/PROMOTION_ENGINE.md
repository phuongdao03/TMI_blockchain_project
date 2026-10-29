# Promotion engine

## Policies

`backend/app/modules/promotions/schemas.py` defines the validated contract.
Prices and discounts use integer VND; percentage rates use basis points.
Rules include service/product scope, fixed/percentage discounts, caps, minimum
and maximum order value, first/returning purchase, stacking, audience AND/OR,
registration cutoff, membership tier, account IDs, expiry, per-account grants,
uses, daily/global redemption limits and budget.

Campaigns transition between DRAFT, SCHEDULED, ACTIVE, PAUSED, ENDED and ARCHIVED.
Claims retain policy/version/title/value/image/terms snapshots. Once claims exist,
core economic rules cannot be rewritten; copy a campaign to change them.
Presentation edits remain possible and budgets cannot fall below commitments.

## Distribution

Preview stores the actor, campaign version, selector hash and eligible account
snapshot in a server-issued token. Confirmation requires that token, a reason,
and an idempotency key. Jobs persist their cursor, result counts and bounded
errors, recheck eligibility and can resume through the periodic worker.
Uniqueness includes account, campaign and issuance slot.

## Media and notifications

Uploads are byte/pixel bounded, decoded with Pillow and normalized to WebP.
Metadata is removed. Soft deletion hides library entries while issued image URLs
remain usable. Library queries defer binary content.
In-app issue/redemption notifications and expiry reminders use persistent
deduplication identifiers. Presentation seen/click/dismiss/opt-out state is stored
on the server. Production write throttles require Redis and fail closed.

## API groups

All paths use `/api/v1` and the existing success/error envelopes.

- `/admin/promotions`: campaigns, lifecycle, services, settings, analytics,
  `analytics.csv`, audit; campaign-scoped previews, recipient search, distribution
  jobs, recipients, stats, redemption pages and CSV.
- `/admin/promotion-media`: upload/list/soft delete; public `/promotion-media/{id}`.
- `/vouchers`: offer, mine, redeem-code, detail, claim and presentation events.
- `/checkout-vouchers/quote`, `/payment-orders/{id}/voucher`: authoritative quote
  and pre-provider payment-order voucher changes.

Analytics distinguish nominal grants, reserved discounts, actual discounts and
related net revenue. Related revenue is not an estimate of incremental revenue.
