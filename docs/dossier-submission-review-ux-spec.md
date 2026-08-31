# Dossier submission and reviewer UX - Phase 2

## Objective

Make heterogeneous dossier preparation and independent review understandable
without duplicating the existing versioned dossier schema. Applicants see the
server-defined fields and document rules before creating a draft. Reviewers see
completion state, evidence coverage and the next blocking action before submit.

## Assumptions

- A dossier draft must exist before media can be attached; pre-draft uploads are
  intentionally out of scope to avoid orphan files.
- `schema.fields`, `schema.documentRules`, `schema.requirements` and the locked
  review snapshot remain the sources of truth.
- The four product roles and current backend authorization do not change.

## User flow

1. Choose dossier type and understand its purpose.
2. Review required information and document preparation checklist.
3. Create a private draft, complete dynamic information, upload each document
   into its declared role, then review and submit.
4. Reviewer declares conflict, checks the locked evidence set, completes each 5T
   criterion with evidence, records findings, selects a recommendation, confirms
   the immutable submission checklist, and submits.

## Security and data boundaries

- Never infer accepted formats in the browser; render server-supplied rules.
- Backend continues to enforce MIME, bytes, count, scan state and ownership.
- Reviewer cannot mutate applicant evidence or reference evidence outside the
  locked assigned version.
- Applicant-facing feedback and private notes remain visually distinct.

## Acceptance criteria

- Selecting a dossier type immediately shows required fields, document count,
  accepted formats, maximum size and visibility guidance.
- The create screen explains the post-draft upload and submission steps and is
  usable at 320 px without horizontal scrolling.
- Reviewer sees live criterion/evidence/checklist completion and a precise next
  action; final submit remains blocked by existing validation.
- Light/dark theme tokens, keyboard navigation, loading and error states work.
- Focused tests, lint, typecheck, production build and browser tests pass.

## Commands

```powershell
Set-Location frontend
npm.cmd run test -- --run src/components/dossiers/dossier-create-form.test.tsx src/components/reviews/five-t-scorecard.test.tsx
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npx.cmd playwright test e2e/dossier-review-ux.spec.ts
```

## Boundaries

- Always: reuse dynamic schema and existing upload/review APIs.
- Ask first: pre-draft storage, new document tables, third-party dependencies.
- Never: mock document requirements in production or authorize in the browser.
