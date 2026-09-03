# Flexible dossier evidence and review

## Objective

Allow every versioned dossier type to accept heterogeneous evidence without a
hard-coded mandatory document checklist. Applicants can upload several files,
describe each file's purpose, and reviewers can assess every frozen file before
submitting a type-specific review.

## Confirmed product rules

- A dossier type defines its form, review rubric, suggested evidence groups,
  accepted formats, limits, and visibility; it does not require named documents.
- Submission requires at least one verified file, but no built-in evidence group
  is mandatory.
- Applicants may use the general purposes `PRIMARY`, `PROVENANCE`, `RIGHTS`,
  `ACHIEVEMENT`, `SUPPORTING`, and `OTHER` and provide a human-readable title.
- Existing dossier, API route, storage, audit, snapshot, and blockchain behavior
  remains compatible. Existing submitted snapshots are immutable.
- Blockchain continues to contain hashes only. This feature never broadcasts a
  transaction.

## Interface contract

- `documentRules` remains the versioned server-owned upload policy. New optional
  presentation metadata is additive.
- Review snapshots expose the frozen dossier type code/name/version and the
  evidence role/label needed to group files without resolving mutable catalog
  data.
- Review drafts store one assessment per evidence media ID with status
  `UNREVIEWED`, `VALID`, `NEEDS_CLARIFICATION`, or `NOT_RELEVANT`, plus an
  optional note.
- Existing review draft and submit routes remain unchanged; new fields are
  optional for old clients.

## User experience

- Applicant upload supports a multi-file queue with independent progress,
  failure, retry, and attachment results.
- Reviewer evidence is grouped by business label, never by an unexplained code.
- Reviewer sees checked/total progress and can move through image, audio, video,
  PDF, and downloadable Office/archive files.
- Supplement feedback explains the missing claim or clarification instead of
  requesting an internal document code.

## Testing

- Backend: dynamic rules, submission without mandatory groups, frozen snapshot,
  assessment validation, and current type-specific rubric.
- Frontend: multi-file queue, evidence grouping, assessment controls, mobile
  layout, keyboard access, loading/empty/error states.
- E2E: upload heterogeneous files and complete a reviewer assessment without a
  conflict or mandatory-document gate.

## Boundaries

- Do not delete existing dossier types, submissions, routes, audit history, or
  legacy review data.
- Do not change Mainnet roles, deploy contracts, or send transactions.
- Do not commit or deploy until explicitly requested.

## Success criteria

- Built-in dossier types do not block submission on a named document role.
- Multiple selected files can be uploaded and attached in one user operation.
- Reviewer UI groups files, records per-file outcomes, and has no raw-ID-first
  presentation.
- The latest active version of every built-in dossier type contains its intended
  specialist rubric.
- Format, lint, typecheck, unit/integration, and E2E checks pass.
