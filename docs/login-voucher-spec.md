# Login voucher

## Objective and scope

Confirmed 2026-10-29: show the supplied Golden Voucher after authentication;
claim and persist it per account. Full promotion administration and checkout
discounts are outside this increment. No wallet credits or payment changes.

## Acceptance

- Eligibility correction: only accounts whose roles are exclusively `USER` and
  which have no linked employee profile. Exclude VIEWER, admin, moderator and
  mixed internal roles. API returns no offer/list and rejects claims with 403.

- Authenticated public and dashboard users see an available offer, with the
  supplied image, Vietnamese text, claim action and dismiss action.
- Claims are authenticated, CSRF protected, idempotent and unique per campaign
  and account, including concurrent requests. Account identity comes from
  session.
- Successful claims survive logout, reload and device changes; claimed offers no
  longer prompt. Failed claims remain retryable and show an error.
- A personal voucher page lists saved vouchers and expiry. Default campaign:
  200,000 VND, 60 days from claim, available to eligible USER accounts; no
  invented early-registration cutoff. Campaign content and availability live in
  the DB.
- Dialog fits mobile and desktop, traps focus, supports Escape, and restores
  focus.

## Stack, structure and conventions

Existing Next.js/React Query frontend, FastAPI/SQLAlchemy backend, Alembic.
Backend module: `backend/app/modules/promotions`; API: `api/v1/vouchers.py`.
Frontend: `components/vouchers`; personal page under authenticated dashboard.
Follow existing camelCase envelope API, Python snake_case, typed React
components. Example:
`return SuccessEnvelope(data=data, meta=ResponseMeta(request_id=request.state.request_id))`.

## Plan and verification

1. Persistence and service: add campaign/claim schema and migration; test
   idempotency, account isolation, inactive/expired campaigns and expiry
   snapshots.
2. API: authenticated offer/list and CSRF protected claim; test access
   boundaries.
3. UI: popup in both auth providers and saved voucher page; test failure/retry,
   pending state, dismissal, account switching and successful claim.
4. Verify: `python -m pytest app/tests/test_vouchers.py` (backend cwd),
   `npm --prefix frontend test -- src/components/vouchers`,
   `npm run typecheck:frontend`, focused ESLint/Ruff, browser desktop/mobile.

## Boundaries

Always preserve payment/wallet/auth behavior and existing uncommitted work. Ask
before changing financial redemption, adding dependencies or deployment. Never
accept account ID/value/expiry from claim request or commit secrets. Schema
addition and seed are necessary for authorized account persistence.
