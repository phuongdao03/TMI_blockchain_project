# Advertising System Specification

## Objective

Add paid advertising campaigns for published or publishable dossiers. Owners can choose a configured placement and duration, see capacity for the full requested interval, reserve a slot, and pay with the existing internal wallet. Admins control inventory, pricing, creative approval, and delivery. Paid bookings remain valid when catalog settings change.

## Tech Stack and Existing Modules

- Backend: Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL, Redis/Celery.
- Frontend: Next.js 16, React 19, TypeScript, Vitest, Playwright.
- Reuse `WalletLedger` and `PaymentGateway` for wallet balance and top-ups; never create a second payment ledger.
- Reuse dossier ownership, visibility, membership-cycle, auth, audit, notification, and worker conventions.
- Membership mapping in this repository: MEMBER 0%, SILVER 5%, COMPANION 10%, PRESTIGE 15%. Annual discount allowances follow the brief: 0, 150,000, 600,000, and 2,000,000 VND.

## Commands

- Backend focused tests: `python -m pytest backend/app/tests/test_advertising_inventory.py`
- Backend full suite: `python -m pytest backend/app/tests`
- Backend lint: `ruff check backend/app/modules/advertising backend/app/api/v1/advertising.py`
- Frontend focused tests: `npm test -- --run src/components/advertising`
- Frontend typecheck: `npm run typecheck`
- Frontend build: `npm run build`

## Project Structure

- `backend/app/modules/advertising/`: models, schemas, inventory, checkout, delivery, and admin services.
- `backend/app/api/v1/advertising.py`: authenticated/public API contract.
- `backend/alembic/versions/`: additive advertising migration and default catalog seed.
- `backend/app/workers/advertising_tasks.py`: reservation expiry and campaign lifecycle work.
- `frontend/src/components/advertising/`: advertiser and admin workspaces.
- `frontend/src/app/(dashboard)/advertising/` and `admin/advertising/`: dashboard routes.
- `docs/advertising-system-plan.md` and `docs/handoffs/advertising-system.md`: implementation and operations handoff.

## Code Style

Follow current module conventions: typed service inputs and views, Pydantic request/response schemas, owner-scoped queries, explicit domain errors, and transaction ownership at service boundaries. Money is integer VND. Intervals are UTC, half-open `[start_at, end_at)`. A placement row lock serializes reservation and admin capacity changes; the service then performs a sweep-line capacity check in the same transaction.

## Testing Strategy

- Unit tests: half-open interval and sweep-line edge cases, pricing snapshots, rotation selection.
- Integration tests: reservation, wallet debit, booking confirmation, idempotency, ownership, admin updates, and dossier eligibility in database transactions.
- PostgreSQL concurrency test: simultaneous final-slot reservations must yield one hold and one conflict; SQLite results do not count as proof of row-lock behavior.
- Frontend tests: API states, checkout pending/insufficient balance, and mobile layout behavior.
- No external payment or production deployment during development.

## Boundaries

- Always: preserve existing wallet/payment/dossier behavior; validate all prices, ownership, permissions, status, and availability server-side; keep audit and transaction history immutable.
- Ask first: real-money transactions, production deployment, or a change that alters existing dossier publication/payment rules.
- Never: trust client price/capacity/tier, oversell a placement, double-debit, publish unapproved creative, or edit unrelated in-progress work.

## Success Criteria

- Capacity is checked over the entire half-open interval and never exceeded under concurrent PostgreSQL reservations.
- Wallet debit and confirmed booking commit atomically and are idempotent.
- Membership discounts use the active tier and remaining annual allowance and are snapshotted on the order.
- Campaigns are delivered only when paid, approved, scheduled, active, and tied to a publicly eligible dossier.
- Admin changes do not invalidate paid bookings; expired reservations release capacity with an audit record.
- Users and admins have usable mobile-first campaign and inventory screens backed by real APIs.

## Open Assumptions

- Seed the four placements from the brief and the documented 1,390,000 VND / 720-hour FEATURED_DOSSIER package. Other packages remain admin-configured because the brief does not give their prices or durations.
- Existing account tiers retain their repository names; labels in the advertising UI may use the brief's Vietnamese labels.
- A campaign may be prepared before dossier publication, but delivery eligibility requires the dossier to be publicly published. Dossier publication itself remains independent of advertising.
