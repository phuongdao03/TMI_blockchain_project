# Council evidence-policy guards — 2026-10-30

## Implemented

`CouncilService._validate_policy_decision` applies only when the frozen dossier
snapshot rubric contains `evidencePolicyVersion: "2026.1"`. Legacy snapshots and
historical decisions are unchanged.

- Owner, current-version submitted reviewers and actors with an unresolved
  current-version CONFLICTED assignment cannot decide/vote. Cancelled assignments
  without a submitted review do not count as expert involvement.
- Approval requires `minimumIndependentReviews` distinct non-owner reviewers
  (optional frozen integer 1..10, default 1), no active assignments and all
  submitted recommendations APPROVE.
- Every submitted approving report is revalidated through
  `ReviewService.validate_approval_review`; unresolved criteria, gates and relevant
  evidence contradictions cannot be overridden by a council approval.
- Session closure rechecks current version, deciding voters and closing actor.
  Failures roll back case decisions, dossier transitions and closure atomically.
- Repository locks current-version assignments in ID order before reading reports
  and counts, serializing review submission with approval checks.

## Existing API routes protected

- `POST /api/v1/admin/council/dossiers/{dossier_id}/decision`
- `POST /api/v1/council/cases/{case_id}/vote`
- `POST /api/v1/admin/council/sessions/{session_id}/close`

Existing roles, CSRF protection, conflict declarations, provenance checks,
minutes, audit and payment/publication transitions remain in use. No new API or
database column was needed for this slice.

## Verification

31 tests passed: `test_council_evidence_policy.py` (15),
`test_council_session_service.py` (13), `test_council_api.py` (3).
The new tests first reproduced unsafe decisions before the guard was added.
Ruff check/format, whitespace and mypy for council service/repository passed.
One existing websockets deprecation warning remains.

## Limits and recovery

The existing supplementation/review cycle is the recovery for a non-approving
report. This is **not** a new structured per-criterion disagreement-resolution
workflow. No account identity is inferred from a free-text nominated-subject
name. PostgreSQL concurrency and staging rollout need external verification;
SQLite tests prove service behavior and rollback, not PostgreSQL row locking.
No production migration, deployment or real financial operation was performed.
