# Applicant claims — 2026-10-30

## Implemented

- Existing dossier drafts store private claim statements, pinned criterion keys,
  linked media IDs and an optimistic-concurrency revision. Existing ownership,
  mutation-role and editable-state guards apply to the new claims write route.
- `PUT /api/v1/dossiers/{id}/claims`: expectedRevision + claims; 409 stale write,
  422 unknown criteria, foreign/duplicate evidence, duplicate claim IDs or bounds.
  Drafts may be incomplete. Submission revalidates references and requires each
  present claim to contain a substantive statement and supporting evidence.
  Empty legacy claims remain valid; no new blanket template requirements.
- Private immutable `snapshot.dossier.claims` uses id, criterionKey, statement,
  evidenceMediaIds; claimsRevision records the acknowledged draft revision. Empty
  legacy snapshots are unchanged. Claims never enter public field projection.
- Applicant editor belongs to the evidence phase and read-only review preview.
  Save acknowledgement, conflict/error retention, explicit discard, unload and
  internal-link guards, unsaved-step/submission blocks and missing-link repair.
- Authenticated active-type version retrieval supports pinned preparation resume:
  `GET /api/v1/dossier-type-versions/{id}` and `dossierApi.getTypeVersion`.

## Migration and recovery

0150_dossier_applicant_claims adds claims_json (empty array) and claims_revision
(zero) to dossiers. No catalog, payments, evidence, certificate or history rows
are changed. Verified upgrade/downgrade/re-upgrade on a temporary SQLite database
containing an old dossier. Downgrade refuses once claim edits exist; use compatible
roll-forward recovery rather than dropping saved content. Production migration
and PostgreSQL recovery have not been executed.

## Verification

- 22 focused backend claims/API/submission/service tests passed; migration test
  passed separately. Scoped Ruff and mypy (four dossier/API files) passed.
- Claim editor + existing workspace tests passed. Browser tests passed on desktop
  and mobile Chrome with page-scoped synthetic API fixtures: successful save,
  criterion/evidence linkage, no horizontal overflow and zero scoped axe findings.
  Screenshots: tmp/dossier-claims-browser-20261030c. These do not prove deployed
  auth, PostgreSQL concurrency or physical-device acceptance.
- The parent branch also contains independent evidence-verification/council work;
  global checks and final acceptance are recorded in the parent handoff.

## Limits

The new editor is an extension of the existing three broad workflow phases, not
a replacement wizard. No live migration, fee change, production deployment or
real transaction was performed. Independent content verification remains a
reviewer responsibility; applicant claims are always presented as self-declared.
