# Voucher verification

## Executed locally

- Promotion policy, audience, management, API, media, distribution, migration,
  reservation, redemption/refund and legacy voucher pytest suites.
- Existing membership and payment service regressions.
- Voucher popup, wallet and checkout-selector Vitest suites; frontend typecheck
  and targeted ESLint; promotion Python typing and Ruff checks.
- Chrome: create/save/publish from Admin; real local API image upload and campaign
  publication; AUTO grant persisted to a local SQLite database; customer popup and
  wallet; desktop/mobile screenshots. Authentication and unrelated portal modules
  use the repository's explicit local E2E shim. No production data is used.
- Zero-net membership purchase with SQLite foreign keys enabled: one purchase,
  no wallet journal, idempotent replay, changed-payload rejection.
- CSV regression with 125 transactions and date filtering.

Exact current command results are recorded in the handoff, not inferred from this
checklist. SQLite verifies transaction behavior but cannot prove PostgreSQL row-lock
contention semantics.

## Required environment validation before release

- PostgreSQL concurrent claims/reservations with competing users and limited budget;
  migration/backfill against a copy of the real schema.
- Actual payOS sandbox lifecycle, duplicate/late confirmations and reconciliation.
- Wire the refund adapter only when a verified refund workflow exists.
- Redis throttle and worker restart/recovery under staging configuration.
- Full integrated dossier/member/advertising browser checkout and cross-browser
  accessibility checks. No real-money transactions without separate authorization.

## Master prompt status

Campaign administration, policies, audience preview/issuance, media, popup, account
wallet, checkout adapters, reporting and audit are implemented. The items above
remain release validation/integration work. Do not describe the entire master prompt
as production complete until these checks are resolved.
