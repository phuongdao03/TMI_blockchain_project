# Payment QR, admin history, and mobile workflow handoff

## Delivered

- Homepage CTAs now use the shared auth context. Signed-in users get the
  personal workspace link; registration and login remain for anonymous users.
- PayOS bank fields are accepted only as bounded strings from the signed API
  response. The payment screen renders its QR and bank details in-page, offers
  transfer-description copy, and has a QR failure state. It no longer links to
  the provider checkout page.
- Migration `0126_payment_initiator_status_history` adds nullable payment
  initiators and status history. New orders record the actor and every actual
  transition in the same transaction. Timestamps remain ordered when the clock
  returns the same instant. Legacy rows were not attributed or backfilled.
- `/admin/payments/history` provides server-side search, status/date filters,
  stable pagination, summaries, transaction detail, status history, and CSV
  export. Reads require `payments.read`; CSV export requires `payments.export`.
  CSV cells are protected against spreadsheet formulas.
- User dashboard creation links stay unavailable while dossier data is loading
  or unavailable. Reviewer overdue badges and ordering refresh on focus and
  every 30 seconds without polling the review API.

## Verification

- Frontend focused suites: 27 passed across homepage, payment screen, payment
  history, payment issuance, applicant dashboard, and reviewer queue.
- Backend payment API/service/PayOS suites: 46 passed.
- Payment migration upgrade/downgrade test: passed on an isolated SQLite file.
- Ruff passed; direct TypeScript check passed with
  `node node_modules/typescript/bin/tsc --noEmit --incremental false`.
- `npm run typecheck` could not run its `next typegen` step because the process
  received `EPERM` opening the already-modified `frontend/next-env.d.ts`.
  Browser verification and production build were not completed.

## Deployment limits

No production database, deployed image, live PayOS credentials, or authenticated
browser session was available for read-only verification. The Alembic migration
is not applied to production, and no deployment or real payment was performed.
