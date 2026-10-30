# Structured dossier and review upgrade — 2026-10-30

This handoff tracks the supplied dossier/evidence/assessment master prompt.
`MASTER_PROMPT_ACCEPTANCE_2026.md` tracks the earlier UX brief and is not a full
acceptance declaration for this work. No production database, payment, chain
transaction, merge, push or deployment was performed.

## Implemented behavior and code evidence

| Area                   | Implementation                                                                                                                                                | Local acceptance                                                                                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Catalog and narrative  | Migration 0151 copies the latest schemas for the 12 verified built-in codes, adding four distinct Vietnamese narrative fields per type with guidance/examples | Existing fields, requirements, custom types and historical schema bytes preserved; optional new fields avoid inventing mandatory business rules                                      |
| Applicant claims       | `dossiers/service.py:replace_claims`, `_validated_claims`; `dossier-claims-editor.tsx`                                                                        | Claims link a statement, pinned criterion and current dossier evidence; server validates scope and revision; unsaved changes are protected                                           |
| Submission version     | Existing `DossierVersion`, `DossierService._snapshot`                                                                                                         | Private claims join frozen form/rubric/evidence hashes; existing snapshots and explicit public projections are unchanged                                                             |
| Content verification   | `reviews/service.py:_validated_evidence_assessments`, `_attribute_verifications`; `review-evidence-assessments.tsx`                                           | Relevance remains distinct from content verification; method/source/scope/limitations and server attribution; incomplete drafts can be saved                                         |
| Criterion safety       | `_validate_verdict_decision`, `validate_approval_review`; `verdict-review-form.tsx`                                                                           | No default success; insufficient basis requires supplementation without manufacturing a citation; unsuitable/contradictory evidence cannot support approval under the new policy     |
| Independent approval   | `CouncilService._validate_policy_decision`, `CouncilRepository.submitted_review_reports`                                                                      | Current owner, submitted expert reviewer or conflicted actor cannot decide under the new frozen policy; configured minimum defaults to one; submitted reports are revalidated        |
| Structured supplements | `supplements/{models,repository,service,schemas}.py`, shared panel                                                                                            | Version/criterion/optional claim, reason, concrete request, priority and explicit optional deadline; append-only sequenced replies/resolutions/reopening, optimistic revision checks |
| Workflow guards        | Existing dossier resubmit and council decision paths                                                                                                          | Open requests block resubmission before snapshots/financial changes; unresolved requests block approval; dossier row locks serialize mutations                                       |
| Preparation recovery   | Authenticated pinned-version endpoint and create-form recovery                                                                                                | A catalog upgrade does not silently replace a restored preparation's schema or fields; loading/error/retry/inactive-template cases covered                                           |
| Regression boundaries  | Existing payment, wallet, fee, certificate and precheck paths                                                                                                 | Retain existing fees, policy snapshots, encrypted notification event, certificate and publication rules                                                                              |

Backend module paths are relative to `backend/app/modules/`; frontend components
are under `frontend/src/components/`. Detailed contracts and first audit are in
`docs/specs/structured-dossier-review-2026.md`, `dossier-applicant-claims.md`,
`council-evidence-policy-guards.md` and `structured-supplements.md`.

Verified built-in codes: CULTURAL_WORK, TRADEMARK, ARTWORK, DOCUMENT,
CERTIFICATE, PERSON, ORGANIZATION, PRODUCT, CULTURAL_HERITAGE, INITIATIVE,
INTELLECTUAL_ASSET, OTHER. No code or name is invented or renamed.

## Data and compatibility

`Dossier.claims_json` and `claims_revision` extend the existing dossier, rather
than adding a second application workflow. Claims contain stable IDs, criterion
keys, statements and evidence media IDs. Each submitted snapshot carries its
private claims. Existing versions remain the source for later expert decisions.

Verification extends the existing review JSON. Files are never verified by
upload, checksum, hash anchoring, membership or payment. Client attribution is
ignored; the authenticated reviewer and server clock are authoritative. Legacy
relevance- only saves cannot silently discard an existing verification, even
when a file or the entire assessment map is omitted. Changes generate existing
sealed audit events containing identifiers/outcomes, without free-text evidence
contents.

`evidencePolicyVersion: "2026.1"` freezes stricter criterion and independence
guards for new templates. Criteria may explicitly enable `allowNotApplicable` or
`verificationRequired`; no universal external certification is introduced.
`minimumIndependentReviews` is an optional integer from 1 to 10, default 1.
Publishing these new configuration flags requires the explicit policy version,
so configuration cannot silently promise an inactive verification guard. Exact
normalized boilerplate reused across approving criteria is rejected; each needs
its own rationale. The software does not infer the truth of a professional
opinion. Old rubric snapshots keep their established rules. Structured request
guards also protect legacy dossiers when staff explicitly create new requests
for them.

Supplement request rows reference the frozen dossier version and criterion
label. Optional claim references must exist in that version. Entries contain
RESPONSE, RESOLVE or REOPEN and increasing per-request sequence numbers.
Existing messages are never overwritten by an endpoint. Internal actor IDs
remain server-side in the persistence/audit records and are excluded from
applicant DTOs.

## APIs and permissions

| Route                                                  | Boundary                                                                                                                                                             |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/dossier-type-versions/{versionId}`        | Authenticated form access; parent type must still be active                                                                                                          |
| `PUT /api/v1/dossiers/{id}/claims`                     | Existing mutation role/scope and editable state; expected claims revision; evidence must belong to current draft                                                     |
| Existing reviewer assignment draft/submit routes       | Assigned reviewer, cleared conflict, locked snapshot; existing CSRF and role checks                                                                                  |
| Existing admin council decision, vote and close routes | Existing authority plus frozen policy separation/completeness guards                                                                                                 |
| `GET /api/v1/dossiers/{id}/supplement-requests`        | Owner or eligible current assigned staff/admin; unreleased OPEN requests are hidden from owner outside NEEDS_SUPPLEMENT; answered/resolved history remains available |
| `POST` to that request collection                      | Eligible current staff/admin, active review, expected version ID, frozen criterion/claim validation                                                                  |
| `PUT .../{requestId}/response`                         | Owner only, NEEDS_SUPPLEMENT only, OPEN request and expected revision                                                                                                |
| `POST .../{requestId}/resolve`                         | Eligible staff/admin, active review and expected revision; explicit resolution or reopening reason                                                                   |

All writes retain existing CSRF protection. Assignment membership alone does not
grant reviewer access after role withdrawal or a conflict. Owning the dossier
does not grant staff authority to resolve one's own requests. Request lists are
bounded to 100 records per dossier, matching the explicit creation limit; this
is an operational limit, not a fee or certification rule.

## Applicant and reviewer operation

The seven business activities fit the existing preparation/completion stages:
choose a type; declare subject information; add its type-specific narrative;
state criterion claims; attach/link evidence; inspect the dossier; submit
through the existing fee policy. Preparation recovery/autosave and uploads are
reused. The claim editor provides explicit save/discard and concurrency errors.

Reviewers see frozen applicant claims beside each corresponding criterion,
without adopting self-declarations as conclusions. Relevance and content checks
are separate. Uncited relevant contradictions still prevent approval. Missing
sources can be recorded as insufficient basis with a concrete applicant request.

Staff save structured supplement items, then use the existing admin request-
supplement transition to release them and send the existing encrypted notice.
Saving an item alone does not send a notice or alter dossier/payment state.
Owners reply and add documents through existing editable dossier controls; every
open item must be answered or resolved before resubmission. Staff then verify
and resolve the items, preserving earlier entries and versions. No duplicate fee
is introduced by creating, responding to or resolving requests.

## State mapping

Existing dossier states remain DRAFT, SUBMITTED, PRECHECK, NEEDS_SUPPLEMENT,
UNDER_REVIEW, COUNCIL_REVIEW and existing decision/payment/anchor/certificate/
publication/revocation states. Payment, relevance, verification, assignment and
supplement statuses remain separate axes. No expanded catch-all enum is added.

Supplement states are OPEN -> ANSWERED -> RESOLVED; a documented staff REOPEN
returns to OPEN without deleting entries. Existing dossier transition services
remain authoritative. A request on an earlier version must still be resolved
before approval of the current dossier.

## Migrations and recovery

1. 0149 appends evidence-policy template versions for the 12 built-in types.
2. 0150 adds private claims JSON and optimistic revision to dossiers.
3. 0151 appends enriched narrative template versions, preserving other schema
   data.
4. 0152 adds structured supplement requests and sequenced response/decision
   rows.

All were exercised only in temporary SQLite databases. Template downgrades
refuse to remove versions referenced by dossiers or saved preparations,
including alternate UUID text forms. Claims downgrade refuses edited data.
Supplement downgrade refuses any request/response history. Recovery after use is
compatible roll-forward or an approved backup restore, never automatic deletion
of live data.

Before staging: capture database/object-store backups, apply reviewed revisions,
check old and new dossiers with real role accounts, exercise sandbox payments
and concurrency, and verify restore. Do not deploy old application code that can
ignore new history or policy guards while keeping new-policy dossiers active.

## Verification record

Final consolidated checks passed: 153 backend tests across the affected business
flows and four migration roundtrips; the full frontend suite passed 1,018 tests
across 239 files. Ruff lint and formatting passed across the backend. Targeted
mypy, frontend typecheck and the browser cases below also passed. The optimized
Next.js production build passed, including its TypeScript/static-page checks.
Full backend mypy passed across 485 source files. Frontend ESLint reported no
errors and four pre-existing unused-variable warnings in the untouched
membership chat administration component. Generated test-server configuration
was restored; build output and synthetic evidence remain outside the delivered
source diff.

Six Chrome cases passed for claims, verification and structured supplementation
across desktop/mobile. They include overflow checks and axe scans limited to the
changed panels. They use synthetic API fixtures and do not prove deployed
provider behavior. Evidence is in
`tmp/structured-dossier-final-browser-20261030/`. Ten additional desktop/mobile
Chrome regression cases passed for the critical applicant/payment/certificate
journey and reviewer submission/tablet/dark-mode paths, in
`tmp/structured-dossier-regression-browser-20261030/`.

## Remaining acceptance limits

- PostgreSQL locking/concurrency and deployed migration/restore are unverified.
- Real authentication/MFA, notification delivery, provider sandbox
  reconciliation, chain signing, physical Safari/Android and measured CWV
  require staging/devices.
- There is no separate adjudication entity for per-criterion expert
  disagreement; recovery uses existing assistance, supplement, version and
  independent review routes. Submitted opinions are not silently replaced.
- New narratives are optional until an authorized template version changes their
  required rules. There is no new graphical template governance console.
- Supplement items identify a criterion/optional claim, not arbitrary per-field
  unlock policies. Existing editable dossier controls remain the allowed
  surface.
- Migration 0152 must be applied before enabling this code against a deployed
  DB.

This is local implementation evidence, not a declaration that every item in the
master prompt or production rollout has been accepted.
