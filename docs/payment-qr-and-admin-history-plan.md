# PayOS QR and admin payment history plan

## Objective

Keep payment creation and confirmation inside the Tinh Hoa Viet site, give
authorized administrators a searchable payment ledger, and keep applicant and
reviewer actions clear on mobile.

## Current findings

- FastAPI, SQLAlchemy, Alembic and Next.js are the existing stack.
- PayOS responses already provide a signed QR payload; the current provider
  adapter only exposes the payload and checkout URL.
- `payment_orders` stores the current transaction snapshot. `payment_events`
  stores verified provider callbacks, but not all local status transitions or
  the account that initiated the checkout.
- The in-progress payment UI renders a QR but still offers an external checkout
  link. Admin reconciliation currently returns at most 50 orders.
- The homepage account actions are static. Existing public shell actions already
  use the shared auth context.
- Existing dossier submission and reviewer UX specs define the wider workflow;
  this change preserves their APIs and permission rules.

## Ordered slices

1. Make homepage actions reflect verified auth state; add a regression test.
2. Expose validated PayOS bank/transfer fields, render its QR in-page, remove
   the ordinary checkout redirect/link, and retain bounded status refresh.
3. Add an additive Alembic migration for the initiating user and append-only
   payment status history. Record initial and subsequent states in the same
   transaction as each payment change. Leave legacy initiator/history unknown
   rather than inventing records.
4. Add capability-protected admin history queries with date/status/search
   filters, stable pagination, summaries, detail, and CSV export.
5. Add a dedicated responsive admin history page. Preserve the existing fee
   issuance workflow and reviewer/user authorization.
6. Correct the user dashboard's create action while dossier data is pending or
   unavailable, and refresh reviewer overdue priority as time passes.
7. Run focused tests, migration upgrade/downgrade checks, lint, typecheck and
   production build. Use browser checks where a local authenticated backend is
   available.

## Acceptance criteria

- Authenticated homepage visitors see their workspace action, not register or
  login links; anonymous visitors retain those links.
- Normal payment flow never opens or redirects to PayOS checkout. QR data comes
  from the verified PayOS response and status remains backend-authoritative.
- Every new payment order has an initiating account and every actual status
  change is recorded once with its source and time.
- Admin history is authorized by `payments.read`, paginated, searchable,
  filterable, exportable and consistent with persisted payment rows.
- Existing payment, dossier, review, billing and authorization behavior stays
  covered by focused regression tests.

## Implementation status

- All feature slices are implemented in the local worktree. See the handoff for
  checks that need a writable Next build environment or authenticated browser.
- Migration `0126_payment_initiator_status_history` is additive and was tested
  through SQLite upgrade and downgrade. Legacy initiators and status histories
  remain unknown; no history was backfilled.
- See [the handoff](handoffs/payment-qr-and-admin-history.md) for verification
  results and deployment limits.

## Verification commands

```powershell
npm.cmd --prefix frontend run test -- --pool=forks --maxWorkers=1 <focused-tests>
python -m pytest backend/app/tests/<focused-tests>
npm.cmd run lint
npm.cmd run typecheck
npm.cmd --prefix frontend run build
```

Production database state, deployed commit/image and PayOS production secrets
must be reported as unverified unless the deployment environment supplies
read-only evidence.
