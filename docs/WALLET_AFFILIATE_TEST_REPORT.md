# Wallet and Affiliate Test Report

## Latest verification

- Final backend focused verification: **74 passed, 23 warnings** in 84.59s;
  **Ruff passed** for all changed backend files. Both checks were run locally.
- After the last dossier service-code normalization, `test_payment_service.py`
  was rerun: **25 passed**; Ruff also passed for that file.
- Frontend focused verification: **90 passed across 11 files**; TypeScript
  passed; lint exited 0 with zero errors and four existing warnings in
  `membership-chat-access-admin.tsx`.
- Production build and live browser smoke were not completed. Local Next dev
  startup failed while acquiring its `.next` lock; a separate dist directory
  also returned `EPERM` when Next tried to create it.
- No real payOS transfer was made during tests. Payout gateway tests use a mock
  HTTP transport; live execution remains gated off by default.
- This is focused verification, not a claim that the full system or a live
  payout flow is production-ready.

## Relevant test files

| Area | Files |
|---|---|
| Finance ledger and migration | `backend/app/tests/test_wallet_finance.py`, `test_wallet_finance_migration.py` |
| Withdrawal review and payout lifecycle | `backend/app/tests/test_wallet_withdrawal_service.py`, `test_wallet_payout_gateway.py`, `test_wallet_api.py` |
| Affiliate service, API, and schema migration | `backend/app/tests/test_affiliate_service.py`, `test_affiliate_api.py`, `test_affiliate_migration.py` |
| Existing customer wallet and collection payment | `backend/app/tests/test_wallet_api.py`, `test_wallet_service.py`, `test_payos_gateway.py`, `test_payment_service.py`, `test_payment_api.py` |

The 74-test result is the aggregate for the exact command below; this document
does not attribute a per-file pass count.

```powershell
# Run from backend/
python -m pytest app/tests/test_affiliate_service.py app/tests/test_affiliate_api.py app/tests/test_affiliate_migration.py app/tests/test_wallet_finance.py app/tests/test_wallet_finance_migration.py app/tests/test_wallet_withdrawal_service.py app/tests/test_wallet_payout_gateway.py app/tests/test_wallet_api.py app/tests/test_registration.py app/tests/test_applicant_upgrade.py app/tests/test_payment_service.py app/tests/test_memberships.py app/tests/test_advertising_inventory.py -q -p no:cacheprovider --tb=short --disable-warnings

# Rerun from backend/ after the final dossier rule-code normalization
python -m pytest app/tests/test_payment_service.py -q -p no:cacheprovider --tb=short --disable-warnings
```

Focused frontend command (run from `frontend/`):

```powershell
npm.cmd run test -- --configLoader runner --run src/components/admin/admin-affiliate-workspace.test.tsx src/components/layout/dashboard-navigation.test.tsx src/components/admin/admin-withdrawals-workspace.test.tsx src/components/wallet/wallet-withdrawal-workspace.test.tsx src/components/affiliate/affiliate-workspace.test.tsx src/components/dashboard/applicant-upgrade-card.test.tsx src/lib/auth/referral-attribution.test.ts src/lib/api/client.test.ts src/components/auth/register-form.test.tsx src/components/auth/login-form.test.tsx src/components/auth/google-oauth-button.test.tsx --reporter=dot
npm.cmd exec tsc -- --noEmit --incremental false
npm.cmd run lint
```

## Implemented behavior represented by the focused suite

- Finance ledger postings, idempotency, and balance constraints.
- Withdrawal reserve, review, payout attempt creation, gateway response
  handling, and reconciliation state changes.
- Affiliate referral/attribution, commission processing, admin review, and
  migration/API behavior, plus privacy-safe referral history and admin profile
  search/suspend/restore.
- payOS payout request signing and response handling through mocked transport;
  no provider money movement was exercised.

## Remaining verification and release work

- Broader frontend suite and production build remain unverified; focused Vitest,
  TypeScript, and lint checks passed. Retry the browser smoke/build in an
  environment where Next can write its dist directory.
- Verify migrations against a disposable database using the deployment
  procedure. Do not use production data for rollback tests.
- Exercise a provider sandbox end to end before any live enablement. Live
  execution requires explicit environment, database, credential, provider, and
  operational/legal gates.
- Reconcile `UNKNOWN` payout outcomes without a provider ID manually with the
  provider before any further action; the reserve remains held.
- Test affiliate reversal after available funds have been partly or fully
  withdrawn. Reversal currently debits the affiliate's pooled available
  balance and cannot complete if that balance is below the commission amount.
