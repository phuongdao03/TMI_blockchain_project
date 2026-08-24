# Reviewer assessment workspace — Phase 1

## Objective

Turn the current 5T scoring form into a controlled reviewer workspace. A
reviewer must declare conflicts, evaluate the locked dossier version, link every
criterion to evidence, record structured findings, and submit an immutable
recommendation.

## Scope

- Keep the four-role model: User, Reviewer, Admin, Super Admin.
- Keep the existing dossier and Council workflows intact.
- Add review-only data for criterion evidence, structured findings, completion
  checklist, and applicant-facing feedback.
- Do not allow a reviewer to change dossier evidence, assign themselves, or make
  the final dossier decision.

## Mandatory submission rules

1. All five 5T scores, explanations, and at least one evidence reference per
   criterion are required.
2. All completion checklist items must be explicitly confirmed.
3. A finding links to one 5T criterion and one or more evidence items from the
   locked version.
4. High and critical findings must be escalated; an approval recommendation
   cannot contain either severity.
5. A supplement or rejection recommendation requires a meaningful
   applicant-facing explanation.
6. Submitted reviews stay immutable. The current assignment workflow remains the
   authorization boundary.

## Commands

```powershell
Set-Location backend; pytest app/tests/test_review_scoring.py app/tests/test_review_scoring_api.py -q
Set-Location frontend; npm.cmd test -- --run src/components/reviews/five-t-scorecard.test.tsx
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

## Verification

- A reviewer cannot attach an evidence ID not contained in their assigned,
  locked dossier version.
- The API rejects incomplete or policy-inconsistent submissions.
- Existing conflict gating and submitted-review immutability still work.
- Keyboard users can select evidence, checklist attestations, and structured
  findings.
