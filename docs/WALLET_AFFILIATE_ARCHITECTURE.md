# Wallet and Affiliate Architecture Audit

## Scope and verified stack

The repository is a Python 3.12 FastAPI service using async SQLAlchemy 2,
Alembic, PostgreSQL/asyncpg, and SQLite for domain tests. Celery and Redis are
already present. The frontend is Next.js 16 App Router, React 19, TypeScript,
TanStack Query, Tailwind CSS 4, Vitest/RTL, and Playwright. This was verified
from `backend/pyproject.toml`, `frontend/package.json`, and the implementation.

## Existing modules to reuse

| Concern | Existing implementation | Finding |
|---|---|---|
| Identity/RBAC | `modules/auth`, `modules/users`, `auth/authorization.py` | Server principals contain roles and permissions. Current system roles include `USER`, `VIEWER`, `MODERATOR`, and `SUPER_ADMIN`; legacy reviewer accounts were consolidated into `MODERATOR`. Role checks must account for mixed roles and privileged permissions. |
| Prepaid wallet | `modules/wallet/models.py`, `wallet/service.py`, `api/v1/wallet.py` | Integer VND `Wallet.balance_minor`, payOS topups, owner-scoped reads, an append-only two-leg `WalletJournal`, idempotency/source uniqueness, row locking, and nonnegative balance protection exist. It is a service wallet, not a withdrawable commission balance or a full multi-account ledger. |
| Payments and payouts | `modules/payments`, `modules/wallet/payout_gateway.py`, `api/v1/{payments,wallet_withdrawals}.py`, `workers/payout_tasks.py` | Collection and a separately gated payOS payout adapter exist. Payout execution requires explicit `finance.payouts.execute` dispatch after approval, and the adapter has separate credentials/signature. `REFUNDED` exists as a status, but a full provider refund workflow was not found. |
| Service purchases | `modules/payments`, `modules/memberships`, `modules/advertising` | Paid dossier fee obligations, memberships, and advertising orders call the affiliate service within their settlement transactions. Legacy dossier `FeeObligation.service_code=STANDARD` is normalized to affiliate rule code `DOSSIER_SUBMISSION`. Wallet topups are not commission sources. |
| Audit/notifications/jobs | `modules/audit`, `modules/notifications`, `db/outbox.py`, `workers` | Reuse the existing audit log, idempotent in-app notification constraint/service, transactional outbox, and Celery infrastructure. |
| User wallet UI | `app/(dashboard)/wallet`, `components/wallet/{wallet-workspace,wallet-withdrawal-workspace,bank-accounts-panel}.tsx` | Prepaid wallet, affiliate totals, and withdrawal/bank-account surfaces exist; focused frontend checks pass. |
| Admin UI | `components/admin/admin-withdrawals-workspace.tsx`, `admin-affiliate-workspace.tsx` | Withdrawal review and affiliate profile/referral/commission/rule workflows exist; focused frontend checks pass. |

## Missing capabilities and risks

- Finance accounts/journals, bank-account storage, withdrawal requests,
  reserve/release, manual approval, payout attempts, a payOS adapter, dispatch,
  and payout-ID polling are implemented behind closed gates.
- Affiliate models, service, attribution/commission APIs, admin profile/referral/
  rule/commission routes, and dashboard data paths are implemented. Focused
  backend and frontend verification is recorded in `WALLET_AFFILIATE_TEST_REPORT.md`.
- Existing `WalletJournal` has an equal/opposite counter amount, but no account
  chart, typed debit/credit entries, actor/audit reference, or accounting for
  commission liability. It must not be relabeled as a full double-entry ledger.
- No verified KYC/tax eligibility workflow or supported bank BIN catalogue was
  found. These prevent safe live payout activation.
- Provider collection credentials do not authorize payouts. The payout adapter
  uses separate payout settings and a signature distinct from
  payment-request/webhook signatures. Provider-supported banks/categories and
  account eligibility must be checked for the real merchant account.
- Automated polling queries by provider payout ID. An unknown outcome without
  an ID remains reserved for manual provider resolution; there is no payout
  detail endpoint or callback. The adapter also does not implement payOS list,
  estimate-credit, or payout-balance operations.
- No commission can be inferred from a draft or order creation. Wired hooks
  execute only on paid dossier obligations, memberships, and advertising
  orders; commission rules use the normalized service code, and source
  references must be unique.
- Refund status alone is insufficient to reverse commission. A refund source
  record and partial-refund policy are required.

## Design decisions

1. Preserve `wallets` and `wallet_journals` for prepaid service spending. Never
   use `balance_minor` for withdrawal eligibility.
2. Add an independent balanced finance journal with user commission-available
   and commission-reserved accounts plus platform counterpart accounts. Derive
   balances from immutable postings and serialize writes by locking the user's
   account rows. Journal source and idempotency keys are unique.
3. Create withdrawal request, immutable bank-account snapshot, reservation, and
   audit/notification records inside one database transaction. Every request
   starts `PENDING_REVIEW`; a separately authorized operator must dispatch a
   payout after approval.
4. Rejection/cancellation releases the reserve exactly once. A provider timeout
   or unknown result keeps the reserve and moves the request to
   `RECONCILIATION_REQUIRED`; it must never trigger a second create call.
5. Store encrypted bank details and expose only masked account numbers. Bank
   BINs must come from a verified enabled catalogue; arbitrary client strings
   are rejected.
6. Automatically create affiliate profiles only for eligible ordinary USER
   identities. A privileged role or admin/reviewer capability excludes the
   account even when USER is also present. Preserve history on suspension.
7. Attribute at most one direct affiliate per customer and order. Store the
   selected rule/version and calculation snapshot. Level-two payouts and
   automatic commission approval remain disabled.
8. Payout, withdrawal, affiliate, and commission execution are backend feature
   gated. Live payout remains false until provider credentials, legal/identity
   gates, operations, and reconciliation have been confirmed.

## Integration map

```text
Verified service payment / membership / advertising settlement
                       │
                       ▼
              Affiliate eligibility
                       │
          locked attribution + rule snapshot
                       │
                       ▼
 PENDING → [manual finance approval] ─┬→ AVAILABLE (no remaining hold)
                                      └→ ON_HOLD → maturity release → AVAILABLE

User bank account → withdrawal request + reserve → PENDING_REVIEW
                                                   │ admin decision
                         reject/cancel ◄───────────┤ approve
                         release reserve           ▼
                                      QUEUED → PROCESSING
                                                  │
                           unknown ────────────────┤
                           reserve held            ▼
                           RECONCILIATION_REQUIRED
                                       SUCCEEDED / FAILED
```

## Provider research

The official payOS API documents payout create/query/list, estimate-credit, and
payout-account-balance endpoints. The implemented adapter currently uses create
and query-by-ID. Create operations require `x-idempotency-key` and `x-signature`;
payout signatures use their own checksum key/format. The repository uses direct
HTTPX, keeping payout signing separate from collection. See
[payOS API](https://payos.vn/docs/api/), [Python SDK](https://payos.vn/docs/sdks/back-end/python/),
[payout signature guide](https://payos.vn/docs/tich-hop-webhook/kiem-tra-du-lieu-voi-signature/),
and [Kênh Chi onboarding](https://payos.vn/dang-ky-dich-vu-chi-ho/).

## Files inspected

Backend: finance models/services, `modules/wallet/payout_gateway.py`,
`workers/payout_tasks.py`, `api/v1/wallet_withdrawals.py`, affiliate service and
API, auth capabilities, audit/notification infrastructure, and migrations.
Frontend: wallet withdrawal and bank-account surfaces, admin withdrawal and
affiliate workspaces, and referral capture/dashboard; focused tests, TypeScript,
and lint passed. Production build and live browser smoke remain unverified.

## Follow-up

Implementation contract and release gates are in
`WALLET_AFFILIATE_SPEC.md` and `WALLET_AFFILIATE_IMPLEMENTATION_PLAN.md`. The
system is not production payout-ready until legal and provider gates are met.
