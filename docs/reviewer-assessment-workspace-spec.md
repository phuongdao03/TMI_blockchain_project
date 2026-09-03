# Reviewer assessment workspace — Phase 2

> Phiếu điểm số trong tài liệu này được giữ để đọc dữ liệu cũ. Thiết kế áp dụng
> cho hồ sơ mới được thay thế bởi
> [verdict-based-review-spec.md](./verdict-based-review-spec.md).

## Objective

Turn the current 5T scoring form into a controlled reviewer workspace. A
reviewer must declare conflicts, evaluate the locked dossier version, link every
criterion to evidence, record structured findings, and submit an immutable
recommendation.

## Professional 5T rubric

Each criterion is scored from 0 to 20 against observable evidence, not the
reviewer's general impression:

| Band  | Meaning          | Required interpretation                                         |
| ----- | ---------------- | --------------------------------------------------------------- |
| 0–4   | Critical failure | Missing, contradictory, unlawful, or unverifiable evidence.     |
| 5–8   | Weak             | Material gaps create a high decision risk.                      |
| 9–11  | Conditional      | Partly supported but requires clarification or supplementation. |
| 12–15 | Meets standard   | Sufficient, consistent evidence for the expected standard.      |
| 16–18 | Strong           | Complete evidence with independent corroboration.               |
| 19–20 | Exemplary        | Exceptional evidence, traceability, and sustainable practice.   |

The five criteria are: factual integrity; transparency and traceability;
ownership, rights, and accountability; professional quality and execution; and
legal, ethical, and stakeholder respect. Every score requires a rationale and at
least one reference from the locked evidence set. A rationale must contain at
least 20 meaningful characters so an unexplained score cannot be submitted.

## Decision gates

- **Recommend approval:** total at least 75/100, every criterion at least 12/20,
  and no unresolved high or critical finding.
- **Request supplementation:** a recoverable evidence gap exists and at least
  one structured finding specifies what must be supplied.
- **Recommend rejection:** total below 50/100 or a critical finding makes the
  dossier ineligible. The reviewer must explain the grounds to the applicant.
- The score supports professional judgment; it does not replace the council or
  authorized final decision.

## Controlled workflow

1. Accept assignment and declare independence before accessing evidence.
2. Verify dossier version, evidence inventory, integrity, and completeness.
3. Assess each 5T criterion using score anchors, cited evidence, and rationale.
4. Record each material issue as a structured finding with severity and action.
5. Select a recommendation that passes the decision gates.
6. Complete the pre-submit attestation and review the decision summary.
7. Submit once; the exact review snapshot is locked and audited.

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
