# Dossier Submission Payment and TEST Isolation

**Status:** Core submission-fee and TEST-isolation behavior is implemented. This handoff also records the Affiliate completion in migration 0164. No production migration, deployment, or real payment was made.

## Behavior

- New dossier-submission fee policies are global across dossier types. The Admin form prefills 5,000,000 VND; an Admin must set the effective window and approve the policy before it applies.
- A fee-bearing submission stays in PAYMENT_PENDING until payment. Only then is the official submitted timestamp and review event recorded. An approved waiver or TEST skip can finalize submission without a real payment.
- Admins can invite a new applicant with the existing USER role and an immutable server-side TEST marker. TEST applicants can skip the fee or simulate success/failure.
- TEST records cannot use real wallet top-ups/payments or withdrawals, generate affiliate commission, issue certificates, publish, or create blockchain anchors. Financial payment history defaults to REAL and supports TEST and ALL filters.
- A permitted Admin can grant a full submission-fee waiver directly with an audit record. Existing request/approval endpoints and waiver history remain for compatibility.
- Affiliate links use 10-character short codes. Migration 0164 keeps each existing code as an alias to the same profile, so previously shared links remain valid.
- Affiliate policies support at most two commission levels. Level 2 stays off at 0% by default; an Admin must set its rate in a draft and publish that version before it takes effect. No rate was preselected or activated.
- Affiliate users can copy or share their short code/link, see registrations and key balances first, and expand secondary metrics. Admin profile search and history use email, referral code, or user ID and show referrals, commission levels, and audited status changes.
- Dossier evidence rows show the original filename and upload safety-check state. Private document verification is labeled as a comparison against the submitted file and does not re-upload or save the selected file.

## API and schema changes

- POST /api/v1/admin/test-applicant-invitations
- POST /api/v1/admin/fee-waivers/grant
- POST /api/v1/payment-orders/{order_id}/test-simulation
- X-Test-Payment-Mode: SKIP|MOCK on dossier submission for TEST accounts only.
- Migration 0164_affiliate_short_codes_and_two_levels adds short-code aliases and configurable level-2 commission fields.
- Migrations 0161_global_dossier_submission_fee, 0162_pending_submission_snapshots, 0163_test_account_isolation, and 0164_affiliate_short_codes_and_two_levels are required.

## Verification

- Root and frontend lint/format checks pass. Frontend TypeScript, backend mypy (504 source files), and the optimized Next.js production build pass. All 10 root tests pass.
- The full frontend suite passes: 1,079 tests across 248 files. Focused Affiliate/Admin/dossier/upload/API-client tests pass: 62 tests.
- The full backend suite reported 1,362 passed, 3 skipped, and 1 failure caused by a test stub missing the newly exposed evidence filename. The stub was fixed; the affected evidence and Affiliate API/service/migration set then passed all 13 tests. The full backend suite was not rerun after this test-only fix.
- The desktop E2E run reported 116 passed, 4 failed, and 9 skipped. The account and dossier selector failures were fixed, and their desktop/mobile CI-mode retest passed all 4 tests. The two remaining failures were the local navigation DevTools overlay and an existing voucher route expectation; neither is part of this change. The full E2E run was not repeated.
- PostgreSQL-safe boolean checks, nullable pending version timestamps, JSON payload typing, and narrow payment-history filter columns address the reported CI failures.

## Operations

Apply migrations only through the normal release process after staging verification. Migration 0164 downgrades refuse to discard referral-code aliases or configured/issued level-2 commissions. Earlier downgrades refuse to remove used global policies, pending snapshots, or TEST-marked rows. Existing payment history is retained and classified as REAL by the migration default.

## P0 follow-up implementation status — 2026-11-13

- Local code supports explicit confirmation for a global submission-fee policy. The creating Admin can activate it alone after confirmation; other fee types retain separation of duties. The fee workspace presents the current policy first, then version history, with waivers and legacy transactions in expandable sections.
- Admin user details return the server-side TEST marker. Admin → Người dùng offers a separate USER invitation for TEST accounts and explains that existing accounts are not reclassified. Details include role, activity/test status, and user-scoped audit history.
- New manual payment issuance and waivers are limited to approved LEGACY dossiers. Missing global policy quotes now explain that the draft is retained and submission remains blocked.
- Evidence type selection is one backend-driven dropdown at every viewport. Saved files include original name, MIME type, size, safety state, a signed-link view action, delete controls, and collapsed integrity comparison.
- Focused frontend tests: 50 passed. Backend fee policy/submission tests: 17 passed; admin-user/audit tests: 9 passed; payment service/API tests: 35 passed. Frontend lint and direct `tsc --noEmit --incremental false` passed. OpenAPI generation exposes the activation request schema.
- `npm run typecheck` could not complete because Next `typegen` was denied writes to `frontend/.next/types/routes.d.ts` and `frontend/tsconfig.json`. `npm run build` and Playwright E2E could not start because Windows denied writes to the configured Next dist directory; the default Playwright output directory was also unwritable. These are local filesystem failures, not assertion failures.
- Local/staging DB credentials and runtime configuration were unavailable. Migrations 0161–0164 and their applied state were not checked against a database. The public site loaded read-only; `/admin/users` redirected to login, so authenticated deployed UI and all three end-to-end business journeys remain unverified.
- All changes remain local and uncommitted. No database migration, real invitation, payment, production configuration change, or deployment was performed.

## Current P0 verification — 2026-11-13

- `npm run format:check`, frontend lint, backend Ruff lint, direct TypeScript (`tsc --noEmit --incremental false`), and backend mypy passed. Root tests: 10 passed. Full frontend suite: 1,083 passed across 248 files. Full backend suite: 1,367 passed, 3 skipped.
- The first complete frontend run exposed an overly exact test text matcher; the matcher now checks the paragraph copy as a substring, its focused test passes, and the complete suite passes after that correction.
- `npm run typecheck` remains blocked at Next type generation by Windows `EPERM` writes to `.next/types/routes.d.ts` and `tsconfig.json`. `npm run build` was blocked creating the configured Next build directory. Playwright could not start its Next dev server because Windows denied writes to the configured dist directory; its flows did not reach assertions.
- No authenticated staging configuration or database credentials were available. Migration state and responsive browser journeys were not verified against staging. The public site was only inspected read-only; its admin route redirected to login.
- No migration was applied, and no commit, real invitation, payment, production configuration change, or deployment occurred.

## E2E CI follow-up — 2026-11-13

- The first CI run after `baed293` completed 120 tests, skipped 9, and failed two browser tests. The fee test used a non-unique text locator; it now matches the exact amount. The legacy payment test queried a form inside a collapsed disclosure; it now opens the section, and its reset fixture explicitly marks the approved dossier as `LEGACY`.
- The two affected desktop browser tests pass locally together (2/2). The complete E2E matrix was not rerun locally; CI had passed the other 120 tests in the reported run.

## E2E mobile follow-up — 2026-11-13

- The next CI run passed the previous fixes and exposed one mobile TEST-submission click intercepted by the fixed bottom navigation. The E2E now centers the submit action in the viewport before a normal click.
- The mobile TEST-submission spec passed five repeated runs locally in CI retry mode. Full E2E was not rerun locally.
