# Tinh Hoa Việt platform upgrade — 2026-10-22

## Scope and constraints

Implement the supplied master brief incrementally in the existing Next.js 16 / React 19 / TypeScript and FastAPI / SQLAlchemy architecture. Preserve outstanding workspace changes, existing records, permissions, MFA and blockchain issuance controls. No production deployment or real-money transaction. Existing payment work is not a prepaid wallet.

## Architecture and audit

| Journey | Frontend | Backend / persistence | Finding |
| --- | --- | --- | --- |
| Public authentication | `(public)/layout.tsx`, `PublicExperienceShell`, `PublicAuthProvider`, `PublicShell`, homepage account components | `auth/me`, refresh/logout; cookie-backed server session | Shared status exists, but disabled guest query is incorrectly treated as loading; initial SSR user is not reconciled after prop changes. |
| Role workspaces | `(dashboard)`, `DashboardNavigation`, `role-workspaces.ts` | `auth/authorization.py`, authenticated principal and resource policies | Reuse permission-aware navigation; retain backend enforcement. |
| Applicant | `/dossiers`, `/dossiers/new`, `DossierCreateForm`, `DossierWorkspace`, status/timeline components | dossiers API/service, versioned schema, evidence and immutable submitted versions | Existing preparation wizard and evidence/review workspace should be extended, not replaced. Refresh-safe autosave before first draft needs investigation. |
| Review / council | `/reviews`, `/admin/reviews`, council workspaces | reviews/council modules, assignment and conflict checks | Reuse assigned work, decision checks and evidence access. |
| Fees / checkout | `/payments`, `/admin/payments`, payment history workspace | payments service, PayOS adapter, billing catalog versions / obligations | Existing webhook/reconciliation and versioned fee records; uncommitted payment changes must be preserved. |
| Certificates | `/certificates`, `/verify` | certificates / blockchain modules, workers, contracts | Keep proof separate from money; preserve issuance prerequisites. |
| Community / notifications | `/community`, `/notifications` | community / notifications modules | Reuse existing publishing, access and notification infrastructure. Paid membership not established by this audit. |
| Operations | frontend E2E and colocated Vitest tests | backend tests, Alembic, infrastructure scripts, contracts and repository tests | Existing mobile performance audit documents remaining INP and physical-device limitations. |

No internal VNĐ wallet/ledger module was found. Blockchain wallet linkage is a separate feature. Introducing prepaid balances requires additive migrations and an atomic ledger integrated with existing billing and verified payment settlement; renaming checkout to “wallet” would be incorrect.

## Ordered implementation and acceptance

1. **Session foundation (P0):** add focused provider regression tests, then fix guest resolution and refreshed server state. Verify initial guest, SSR user, refresh-only recovery, revoked session, server prop changes and cross-tab changes. Files: auth provider, session-sync and their tests. Run focused Vitest, shell/homepage regressions, lint, typecheck and browser check.
2. **Applicant recovery (P1):** audit draft creation and persistence; extend existing wizard with account-scoped recovery and explicit saved/error state. Verify reload, type change, validation and upload interruption without losing successful evidence. Keep each slice to at most five files.
3. **Reviewer focus (P1):** verify assigned queue/search/filter/mobile cards and supplementation actions; improve missing behavior with authorization regression coverage. Preserve council and conflict-of-interest boundaries.
4. **Wallet foundation (P0 financial risk):** additive wallet, immutable balanced ledger and idempotent transactions; integer VNĐ, nonnegative available balance, row locking and ownership checks. Verify concurrent debit, duplicate settlement, reversal and migration rollback against PostgreSQL before connecting checkout.
5. **Wallet payments (depends on 4):** explicit top-up purpose in existing adapter, verified webhook amount/currency/reference, reconciliation, fee snapshot and atomic obligation settlement. Add wallet UI only against real backend contracts. Fee policy must distinguish submission and finalization without changing existing invoices.
6. **Membership (depends on 5):** admin-configured plans, duration/benefits and explicit purchase/renewal, immutable price snapshot, atomic wallet debit plus entitlement. No implicit recurring charge.
7. **Release verification:** authenticated E2E A–F from the brief, 360/375/390/430/768/1024/1440px, accessibility, provider sandbox, PostgreSQL concurrency, migration/rollback and staging readiness. Report untested hardware/provider requirements explicitly.

## Commands and conventions

- Frontend: `npm --prefix frontend test -- --maxWorkers=2`; `npm --prefix frontend run lint`; `npm --prefix frontend run typecheck`; `npm --prefix frontend run build`.
- Backend: `python -m pytest backend/app/tests`; `python -m ruff check backend`; from backend: `python -m mypy app`.
- Browser journeys: `npm --prefix frontend run test:e2e` (inspect runner configuration before starting).
- Use existing typed DTOs, colocated tests and semantic UI tokens. Example: `const user = useAuthUser();` and `resolveDefaultWorkspace(user.roles, user.permissions ?? [])`.
- No arbitrary fees, fake provider credentials, frontend balance authority or success based on browser redirects.

## Delivery status

User direction after audit: switch collection to wallet payment. Preserve the existing internal fee-issuance policy and immutable order amounts; add explicit wallet confirmation rather than automatically charging. New provider checkout is used for top-ups. Existing provider checkouts must settle or be cancelled before wallet payment to prevent double collection. Implement `GET /wallet`, `POST /wallet/topups`, owner-only top-up retrieval/reconciliation, and `POST /payment-orders/{id}/wallet-payment` with CSRF and idempotency. Top-ups reuse the existing verified provider adapter and webhook URL. No endpoint grants arbitrary credit.

Ledger design: a fixed two-leg journal stores wallet and counter-account deltas together with a database constraint requiring their sum to be zero. Wallet balance updates and journal insertion share one transaction. Each source payment/top-up and each wallet-scoped idempotency key is unique. PostgreSQL locks serialize mutations; guarded balance updates enforce nonnegative balances. Posted journals are immutable; future refunds must post a linked compensating journal rather than edit history.

Audit and implementation are in progress. This document is an execution plan, not evidence that wallet, membership, payment policy or all six phases have shipped. Verification results belong in `docs/handoffs/platform-upgrade-foundation.md`.
