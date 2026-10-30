# Council approval guards — 2026-10-30

## Objective / verified gap

`CouncilService.record_admin_decision` previously checked review count and file
provenance, but did not prevent a dual-role reviewer approving their own review.
`cast_vote` trusted a self-declared no-conflict record; `close_session` checked
provenance without rechecking unresolved review recommendations.

## Contract and compatibility

Use the immutable snapshot rubric `evidencePolicyVersion: "2026.1"` to apply
new checks. Existing snapshots without the policy retain their decision rules.
No new role, database column, payment rule or universal two-reviewer requirement.

- The dossier owner, current-version submitted reviewers and reviewers with a
  current-version unresolved CONFLICTED assignment cannot decide/vote
  on that dossier. Historical declined/conflicted assignments alone do not bar
  a person from later independent work. A cancelled assignment without a
  submitted personal report is not itself an expert review.
- Approval requires all submitted reviews to recommend APPROVE, no unfinished
  assignments, and at least `minimumIndependentReviews` distinct non-owner reviewers.
  The frozen optional integer is 1..10, default 1.
- Apply the same rules in one-admin decisions, council votes and session closure.
  Closure rechecks the current version and every approving voter, so changed
  assignments cannot bypass the guard.
- Reuse `ReviewService.validate_approval_review` for each submitted approving
  report, checking the same frozen criterion/gate/evidence rules as submission.
- Lock current-version assignments before report/count reads to serialize
  concurrent submissions. PostgreSQL concurrency still needs staging validation.

The existing supplement/review route is the recovery for unresolved reports.
This increment does not implement a per-criterion disagreement-resolution record
or infer nominated-subject identity from a free-text name.

## Tasks / tests

1. Reproduce owner/reviewer self-decision and disagreement/count bypasses using
   real SQLite service fixtures.
2. Add repository aggregate queries and shared council service checks.
3. Verify legacy council regression, independent approval, and atomic closure
   rollback after an ineligible vote or stale case.

Run `python -m pytest backend/app/tests/test_council_evidence_policy.py
backend/app/tests/test_council_session_service.py backend/app/tests/test_council_api.py
-q`. Use existing async service/repository patterns and explicit domain errors.
No real database, transaction, blockchain call or deployment is authorized.
