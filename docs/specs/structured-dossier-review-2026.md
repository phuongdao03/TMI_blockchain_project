# Structured dossier and evidence review — 2026-10-30

## Objective and boundaries

Implement the supplied dossier/review master prompt incrementally in the
existing Next.js/FastAPI application. Preserve catalog IDs, fees, wallet/payOS,
certificate history and frozen submissions. No production deployment, real
transactions, database resets or automatic verification of legacy evidence are
authorized.

The supplied prompt authorizes local implementation without another approval
gate. Existing `MASTER_PROMPT_ACCEPTANCE_2026.md` covers a different UX brief
and does not constitute acceptance of this new request.

## Initial source audit and gap matrix (before implementation)

The matrix records the starting gaps. Implemented behavior and final checks are
tracked in `docs/handoffs/structured-dossier-review-2026.md`.

| Function                | Existing implementation                                                                                         | Gap / required change                                                                                 | Risk / priority   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------- |
| Type catalog/forms      | `dossiers/models.py:DossierTypeVersion`, `dynamic_schema.py:validate_dynamic_schema`, `dossier-create-form.tsx` | Reuse versioned schema; richer narrative/claims still needed                                          | Medium / P1       |
| Submission              | `dossiers/service.py:_snapshot`, `DossierVersion`                                                               | Frozen form/rubric/media hashes already exist; explicit applicant claims/links still needed           | High / P1         |
| Draft recovery          | `DossierPreparation`, migration 0144, `use-dossier-preparation.ts`                                              | Existing revision-based recovery; claim editor must join this flow                                    | Medium / P1       |
| Evidence                | `DossierEvidence`, `document_rules.py`, `ReviewService._validated_evidence_assessments`                         | Current statuses express relevance only; missing structured content verification                      | High / P0         |
| Criteria                | `ReviewService._validate_verdict_decision`, `verdict-review-form.tsx`                                           | Evidence IDs alone can support MEETS; unrestricted NOT_APPLICABLE; missing insufficient-basis outcome | High / P0         |
| Intake                  | `reviews/precheck_service.py:PrecheckService`                                                                   | Existing separate transitions; structured intake checklist/reasons still needed                       | High / P1         |
| Assignments/conflicts   | `ReviewService.assign_reviewers`, `declare_conflict`, `_owned_assignment`                                       | Reuse existing assignment scope, conflict and version controls                                        | High / P1         |
| Supplements             | `request_supplement`, `_clone_current_evidence`, review findings                                                | Existing reopen/clone path; item-level deadlines/responses and assessment invalidation still needed   | High / P1         |
| Payment                 | `Dossier.submission_fee_snapshot`, migration 0143; wallet/payment modules                                       | Keep existing policy and payment lifecycle                                                            | High / regression |
| Certificate/publication | Existing certificate/blockchain/public modules                                                                  | No change to issuance conditions or public projection                                                 | High / regression |

Paths above are relative to `backend/app/modules/` unless frontend components or
migrations are named. Presence is source evidence, not production verification.

## Data and contracts: first increment

Extend the existing `reviews.evidence_assessments` JSON, keyed by media ID.
Retain `status` and `note`; add optional `verification` with `outcome`,
`method`, `source`, `scope`, `limitations`. Outcomes: UNVERIFIED, VERIFIED,
PARTIAL, INSUFFICIENT, CONTRADICTED, UNVERIFIABLE. Server records `verified_by`
and `verified_at` for changed verification records; clients cannot choose
attribution. Existing assignment/version foreign keys bind each record to its
reviewer and snapshot. Submitted reviews remain immutable. No file upload/hash
sets these outcomes.

Use unchanged review draft/submit routes and DTO aliases. Add INSUFFICIENT_BASIS
to criterion outcomes; it requires SUPPLEMENT, not approval. Unassessed criteria
remain absent from the draft, never default to MEETS.

Opt-in frozen rubric `evidencePolicyVersion: "2026.1"` enforces:

- MEETS cites at least one relevant (VALID) file and no cited file with
  unresolved clarification, irrelevance, contradiction or
  insufficient/unverifiable content.
- Criterion `verificationRequired: true` additionally requires VERIFIED content
  for every cited file. No external authority is required universally.
- NOT_APPLICABLE requires criterion `allowNotApplicable: true`.
- A recorded verification conclusion includes method, source, scope,
  limitations; drafts may remain incomplete, submission cannot.

Templates without the policy retain their previous rules. No migration mutates
old snapshots or infers old verification results. Migration 0149 appends a
policy version to the 12 verified built-in types for future drafts, copying
their current fields/rules/names. It leaves custom types unchanged.
Administrators can publish further versions through the existing catalog API.
Required content verification remains criterion-specific and disabled unless
explicitly configured.

## State mapping and invariants

| Requested logical state               | Existing state / axis                                  | Guard                                                 |
| ------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------- |
| DRAFT                                 | DRAFT                                                  | Owner edits draft only                                |
| PENDING_PAYMENT                       | submission fee fields + existing payment status        | Existing fee gate                                     |
| SUBMITTED / INTAKE_REVIEW             | SUBMITTED / PRECHECK                                   | Existing precheck authorization                       |
| EVIDENCE_VERIFICATION / EXPERT_REVIEW | UNDER_REVIEW + per-file verification / assignments     | Assigned reviewer, no unresolved conflict             |
| REVISION_REQUIRED                     | NEEDS_SUPPLEMENT                                       | Reason, cloned evidence, new submission version       |
| COUNCIL_REVIEW                        | COUNCIL_REVIEW                                         | Existing council path                                 |
| APPROVED / REJECTED                   | APPROVED / REJECTED                                    | Existing decision service plus completed review rules |
| PUBLICATION_PENDING / PUBLISHED       | Existing payment/anchor/certificate states / PUBLISHED | Existing publication conditions                       |
| WITHDRAWN                             | CANCELLED or REVOKED according to existing operation   | Preserve distinct revocation meaning                  |

Do not add a second workflow enum. Payment, relevance, verification, assignments
and advertising remain separate axes.

## Implementation tasks and acceptance

1. Delivered evidence verification: DTO, normalized persistence, server
   attribution and submit guards. Tests cover incomplete drafts, forged
   attribution, legacy records and contradiction.
2. Criteria safety: frozen policy validation + backend MEETS/NA guards and
   insufficient-basis outcome. Verify schema and scoring tests, legacy cases.
3. Reviewer UI: separate relevance and content verification, no preset intake
   answer, policy-aware completion, read-only state. Verify Vitest, typecheck,
   lint and browser mobile/desktop.
4. Delivered applicant claims/evidence links, optional type narratives, pinned
   preparation recovery, structured supplement requests and independent council
   guards. The existing versioned catalog API remains the template publication
   surface; the existing broad UI stages group the seven business activities.
5. Local regression, migration/recovery and scoped accessibility checks passed.
   Staging/device/deployment evidence remains required; detailed limits and test
   results are recorded in the handoff.

## Commands and code conventions

Backend tests: `python -m pytest backend/app/tests/test_review_scoring.py -q`.
Frontend tests: `npm --prefix frontend test -- review-evidence-assessments`.
Backend lint: `python -m ruff check backend`. Frontend checks:
`npm --prefix frontend run typecheck`, `npm --prefix frontend run lint`,
`npm --prefix frontend run build`. Follow existing Python
service/dataclass/Pydantic boundaries, snake_case DTOs with camelCase aliases,
React controlled inputs and semantic theme tokens. Example:
`raise ReviewValidationError("Criterion evidence must be relevant.")`.

## Recovery

Verification uses existing JSON columns; migration 0149 adds template rows only.
The application preserves recorded verification when a relevance-only client
saves the same file. Downgrade removes migration-created template rows only when
none is referenced by a dossier; otherwise it fails closed and requires
compatible roll-forward recovery. Never remove evidence/history as a rollback
operation. PostgreSQL/staging recovery remains unverified.
