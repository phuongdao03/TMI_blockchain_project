# Implementation plan: dossier submission and reviewer UX

## Phase 1 - Applicant preflight

- [x] Render a four-stage journey and server-driven preparation summary.
  - Acceptance: required fields and every document rule show format, size, count
    and visibility before draft creation.
  - Verify: dossier create component test.
  - Files: dossier create form and test.

## Phase 2 - Reviewer completion guidance

- [x] Add live review progress and next-blocker guidance.
  - Acceptance: criterion evidence, checklist and recommendation completion are
    readable without relying on color; existing submit validation is unchanged.
  - Verify: 5T scorecard component test.
  - Files: 5T scorecard and test.

## Phase 3 - Responsive verification

- [x] Verify applicant and reviewer flows in desktop/mobile light and dark modes.
  - Acceptance: no horizontal overflow and core actions remain reachable.
  - Verify: Playwright, lint, typecheck and build.

## Risks

- Schema variants: use defensive optional rendering and human-readable MIME
  labels.
- Long forms on mobile: keep one column, concise summaries and anchor navigation.
- False completion: reuse the same values that drive final submission validation.
