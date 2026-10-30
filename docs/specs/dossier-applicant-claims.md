# Applicant claims and evidence links

Extend existing dossier drafts with structured applicant statements, linked to a
criterion in the pinned rubric and media already attached to that draft. Claims
are private dossier content and enter the existing immutable submission snapshot.
No public projection, fee, status enum or existing submitted snapshot changes.

## Contract and tasks

1. Add `claims_json` and `claims_revision` to dossiers in additive migration 0150.
   Empty defaults preserve old records. Downgrade refuses to discard saved claims.
2. `PUT /dossiers/{id}/claims` accepts expectedRevision and up to 50 claims, each
   with a stable UUID, criterionKey, statement and evidenceMediaIds. Reuse existing
   mutation role, ownership, editable states and row lock; stale revision is 409.
   Draft statements can be incomplete, but nonempty; unknown criterion/media or
   duplicate identifiers are rejected. Submission validates references again.
3. Add claim editor to the existing applicant workspace. Explicit save, retained
   edits after failure, stale-write feedback, unsaved navigation protection and
   read-only submitted claims. Future schema may opt into mandatory claims; this
   increment imposes none on legacy templates.

## Verification

Backend: pytest `test_dossier_applicant_claims.py`, migration test and existing
submission/service tests. Frontend: Vitest claim editor and workspace tests;
TypeScript and scoped lint. Follow existing dataclass/service/Pydantic boundaries,
camelCase JSON contracts and semantic UI tokens. Never log claim text or perform
production migration/deployment.
