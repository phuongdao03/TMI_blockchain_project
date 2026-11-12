# Dossier Submission Payment and TEST Isolation

**Status:** Implemented in the local working tree. No commit, deployment, production migration, or real payment was made.

## Behavior

- New dossier-submission fee policies are global across dossier types. The Admin form prefills 5,000,000 VND; an Admin must set the effective window and approve the policy before it applies.
- A fee-bearing submission stays in PAYMENT_PENDING until payment. Only then is the official submitted timestamp and review event recorded. An approved waiver or TEST skip can finalize submission without a real payment.
- Admins can invite a new applicant with the existing USER role and an immutable server-side TEST marker. TEST applicants can skip the fee or simulate success/failure.
- TEST records cannot use real wallet top-ups/payments or withdrawals, generate affiliate commission, issue certificates, publish, or create blockchain anchors. Financial payment history defaults to REAL and supports TEST and ALL filters.
- A permitted Admin can grant a full submission-fee waiver directly with an audit record. Existing request/approval endpoints and waiver history remain for compatibility.

## API and schema changes

- POST /api/v1/admin/test-applicant-invitations
- POST /api/v1/admin/fee-waivers/grant
- POST /api/v1/payment-orders/{order_id}/test-simulation
- X-Test-Payment-Mode: SKIP|MOCK on dossier submission for TEST accounts only.
- Migrations 0161_global_dossier_submission_fee, 0162_pending_submission_snapshots, and 0163_test_account_isolation are required.

## Verification

- Backend Ruff lint and format checks pass. The focused affected backend set passes: 46 tests across auth migration/session, dossier submission API, public search, and payment service.
- The full backend run before the final test and migration fixes reported 1,353 passed and 6 failed. Those failures were addressed, and all five directly affected test modules pass; the full suite was not rerun after the fixes.
- Frontend lint and typecheck, root formatting, and all 10 root tests pass. Focused changed-screen tests pass: 23 tests.
- The full frontend run reported 1,070 passed and 4 failed. The stale waiver expectation was corrected and its focused test passes; three unrelated reviewer scorecard/verdict tests remain failing.
- The E2E run displayed all 129 desktop cases but did not return a summary and was stopped. A focused rerun could not start because the local Next dev lock returned `EPERM`/access denied. E2E is not verified clean.
- Backend mypy exited with an internal error in the installed mypy 2.3.0 tool.

## Operations

Apply migrations only through the normal release process after staging verification. Downgrades refuse to remove used global policies, pending snapshots, or TEST-marked rows. Existing payment history is retained and classified as REAL by the migration default.
