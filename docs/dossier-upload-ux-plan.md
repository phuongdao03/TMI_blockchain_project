# Implementation plan: Simplified dossier upload experience

## Phase 1: Input and upload contracts

- Add failing tests for local phone normalization at frontend and API
  boundaries.
- Add failing tests for the 100 MB evidence policy and production request
  boundary.
- Implement normalization and aligned limits without weakening file validation.

## Phase 2: Applicant workflow

- Add component expectations for concise upload instructions and clearer
  actions.
- Simplify the dossier workspace hierarchy and evidence editor.
- Preserve responsive behavior, keyboard controls and existing workflow actions.

## Phase 3: Persisted policy and verification

- Add a reversible migration updating video-capable document rules to 100 MB.
- Run focused tests, formatting, types and production configuration tests.
- Record the final operational environment changes in the handoff.

## Risks

- Provider plan may impose a lower video ceiling: keep the limit at 100 MB and
  surface provider errors.
- Existing document rules live in JSON: update only video-capable rules and
  provide downgrade logic.
- Larger inspection work can take longer: keep existing bounded polling and
  scanner controls.
