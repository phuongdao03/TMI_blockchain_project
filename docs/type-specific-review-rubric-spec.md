# Type-specific review rubric specification

> Phần chấm điểm trong tài liệu này là đặc tả tương thích cho hồ sơ cũ. Hồ sơ
> mới dùng phương thức kết luận tại
> [verdict-based-review-spec.md](./verdict-based-review-spec.md).

## Objective

Extend the existing reviewer workflow so each versioned dossier type can define
mandatory gates and specialist criteria in addition to the shared 5T quality
assessment. The exact rubric is frozen into the submitted dossier snapshot and
remains reproducible after later template changes.

## Assumptions

- `DossierTypeVersion.schema_json` remains the single source of truth for form,
  document, and review requirements.
- The four product roles remain unchanged.
- 5T remains a cross-type quality layer; specialist criteria do not replace it.
- Existing dossier types without `reviewRubric` use the current 5T-only flow.

## Contract

`reviewRubric` is optional in a dossier-type schema:

```json
{
  "reviewRubric": {
    "version": "2026.1",
    "title": "Thẩm định tác phẩm nghệ thuật",
    "gates": [
      { "key": "rights", "label": "Quyền nộp hợp lệ", "description": "..." }
    ],
    "criteria": [
      {
        "key": "originality",
        "label": "Tính nguyên bản",
        "description": "...",
        "weight": 30
      }
    ],
    "thresholds": { "approveMin": 75, "rejectBelow": 50 }
  }
}
```

- Gate answers are `PASS`, `FAIL`, or `NOT_APPLICABLE`, with rationale and
  evidence references. Required gates must pass before approval.
- Criterion scores use 0–5 anchored levels, require rationale and evidence, and
  produce a weighted 0–100 specialist score.
- Criterion weights must total 100; keys are unique; limits are enforced at the
  API/schema boundary.
- Approval requires all required gates to pass, the specialist threshold, and
  the existing 5T decision gates.
- Submitted reviews remain immutable and audit-covered.

## UX workflow

1. Independence declaration.
2. Intake completeness and locked evidence review.
3. Mandatory gate assessment.
4. Type-specific scored assessment.
5. Shared 5T assessment.
6. Findings, recommendation, attestation, immutable submission.

Mobile presents one section at a time with a persistent progress summary;
desktop keeps evidence beside the assessment workspace.

## Testing

- Dynamic-schema validation rejects malformed rubric definitions.
- Dossier submission freezes the rubric in the version snapshot.
- Review submission rejects missing/failed gates, incomplete specialist scores,
  foreign evidence IDs, and decisions inconsistent with thresholds.
- Existing 5T-only dossier reviews remain valid.
- Frontend contract, score calculation, keyboard access, and responsive layout
  receive focused component tests.

## Boundaries

- Never infer rubric by file extension alone.
- Never mutate a rubric version already used by a submitted dossier.
- Never allow total score to override a failed legal, ownership, or integrity
  gate.
- Do not add a parallel dossier-type catalog.

## Success criteria

- Reviewer sees the rubric frozen for the assigned dossier type.
- Server, not frontend, enforces gates and score thresholds.
- Legacy reviews continue working without data migration.
- TypeScript, lint, backend tests, and migration tests pass.
