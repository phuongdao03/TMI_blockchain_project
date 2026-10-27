# Move the dossier fee to submission

Approved by user: 2026-10-27. This replaces the existing post-approval charge
for newly created dossiers, rather than adding a second charge.

## Contract and compatibility

- Add an explicit submission-fee policy marker to dossiers. Existing rows stay
  on the legacy policy, including existing drafts, obligations and paid orders.
- API-created new dossiers use submission charging. At initial submission,
  atomically snapshot the server price, version/evidence, and one pending wallet
  payment order; move to PAYMENT_PENDING. No wallet debit occurs on submission.
- Typed dossiers use the effective STANDARD price catalog entry when configured.
  When there is no effective entry, or a category-only API input has no type,
  use `SUBMISSION_FEE_AMOUNT_MINOR` (default VND 5,000,000). Ambiguous catalog
  entries and non-VND prices fail closed and preserve the draft. Existing
  configured prices are not overwritten.
- Payment confirmation for the new policy records payment and moves to SUBMITTED
  for intake, never PAID/issuance. Supplements reuse payment.
- Successful approval then transitions through APPROVED to PAID (existing
  issuance eligibility state), without another order or wallet debit.
- Cancellations/expiry/retries keep unpaid submissions outside review and
  preserve the original price. New fee checkout remains wallet-only.
- Legacy payment paths retain their existing statuses, callbacks and records.

## Incremental tasks and checks

1. Add policy/snapshot/payment timestamp migration and a bounded submission-fee
   service; prove price snapshot, order reuse/retry, owner isolation and legacy
   row defaults using focused backend tests.
2. Integrate submit/payment/approval transitions; prove retry idempotency, no
   review before payment, no early issuance, no recharge after supplementation
   or approval, and legacy compatibility.
3. Expose backend fee preview/retry and additive policy fields. Update receipt,
   timeline/payment copy and checkout recovery; test relevant UI and browser
   flow.
4. Run backend billing/dossier/payment/council tests, lint/type checks, frontend
   focused tests/build, and document deployment/rollback limits.

## Rollback

Apply only the additive schema before the matching application release. No
production migration or payment is performed here. Once new-policy submissions
exist, rolling back to an old application is unsafe: it treats payment as
issuance. Retain compatible routing code or pause processing of all new-policy
dossiers while rolling forward. Schema downgrade refuses while any new-policy
record exists, including a draft. Never rewrite paid history or convert pending
orders automatically.

## Implemented interfaces

- Migration: `0143_submission_fee_policy` adds `submission_fee_required`,
  `submission_fee_snapshot`, and `submission_fee_paid_at`; all existing rows
  retain `false`/null. API dossier creation opts new rows into the policy.
- `GET /api/v1/dossiers/{id}/submission-fee`: authenticated scoped price
  preview, returning `amountMinor`, `currency`, `description`.
- `POST /api/v1/dossiers/{id}/submission-payment`: owner-only checkout recovery,
  requiring `Idempotency-Key`; returns `paymentOrderId`. Dossier row locking
  serializes reservations; pending orders are reused. Expired/cancelled attempts
  do not change the snapshotted amount or the unpaid review gate.
- Dossier responses add `submissionFeeRequired` and `submissionFeePaidAt`.
  Payment responses add optional `purpose` (`SUBMISSION_FEE` for the new
  policy). Existing endpoints and legacy fields remain available.
- Wallet confirmation, webhook, reconciliation and manual confirmation share the
  policy-aware status transition. Submission payments never enqueue certificate
  issuance or send blockchain-ready notifications.
- Precheck/reviewer assignment require recorded submission payment for the new
  policy. Council approval reuses that payment; legacy fee creation APIs reject
  new-policy dossiers even if their status is APPROVED.

## Validation and release notes

- Backend regression covers initial submit/replay, one wallet debit, precheck
  rejection before payment, no early issuance, supplement without repayment,
  catalog override and immutable snapshot, cross-owner rejection, cancellation,
  expiry/retry, approval gates, old records and guarded schema downgrade.
- API contract tests cover price preview, required retry key and forbidden
  access.
- All 454 backend application source files pass mypy. Focused Ruff checks pass.
- Full frontend run passed 922 tests; an additional draft/pricing-error recovery
  case and updated public guidance were subsequently verified in focused tests.
  Frontend lint has zero errors/five pre-existing warnings; typecheck/build
  pass.
- Playwright checkout recovery → payment result passes on desktop and mobile;
  exact widths 360/375/390/430/768/1024/1440 have no overflow or page errors.
  These browser cases use fixtures, not live payments. Evidence is in
  `docs/ux-evidence-2026-10-27/submission-fee-390.png` and
  `submission-fee-1440.png`.
- Apply the schema before deploying the matching API/workers/frontend. Compose
  passes the new amount setting. Existing payment settings remain for legacy
  dossiers. No deployed database, paid order or wallet balance was modified.
- Real PostgreSQL reservation contention and payment-provider sandbox acceptance
  still need staging. Do not equate SQLite/fixture verification with production
  integration or a completed sitewide UX transformation.

## Final checks

A 64-case backend regression run passed. The final payment/API follow-up passed
39 cases; all five submission-fee/migration cases passed after the final guards.
Provider webhooks cannot claim wallet-only orders by code; reconciliation does
not settle wallet orders through an external provider. Existing provider
deprecation warnings remain.
