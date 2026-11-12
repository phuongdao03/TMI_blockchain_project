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
