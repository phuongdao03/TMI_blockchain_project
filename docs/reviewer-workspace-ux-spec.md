# Reviewer workspace UX correction

## Objective

Clarify operational ownership and make the reviewer workspace feel like a
focused professional review tool:

- Admin sees dossier metadata, selects an active reviewer, and assigns work.
- Admin does not preview or evaluate dossier evidence during assignment.
- Reviewer opens the locked evidence version, assesses it, saves a draft, and
  submits a recommendation.
- Admin reads the completed reviewer report and performs the existing final
  decision step.
- Autosave occurs once after meaningful edits settle and never loops because of
  cache-driven rerenders.

## Commands

- Focused frontend tests:
  `npm --prefix frontend test -- --run src/components/admin/review-assignment-queue.test.tsx src/components/reviews/five-t-scorecard.test.tsx src/components/reviews/review-assignment-list.test.tsx`
- Quality: `npm run lint && npm run typecheck && npm run format:check`
- Production build: `npm --prefix frontend run build`

## Project structure

- `frontend/src/components/admin/`: assignment-only admin experience and
  reviewer report/final decision states.
- `frontend/src/components/reviews/`: reviewer queue, workspace, evidence, and
  assessment form.
- `frontend/src/app/(dashboard)/reviews/`: reviewer route composition.
- Colocated `*.test.tsx`: role-boundary, autosave, and UX regression coverage.

## Code style

Use existing Tailwind theme tokens and semantic HTML. Prefer a compact task
header, a clear primary work column, a supporting evidence rail, visible focus
states, and restrained status surfaces over repeated equal-size cards.

## Testing strategy

- Prove admin pages no longer render evidence preview or manual precheck notes.
- Prove assignment from submitted/precheck states performs required internal
  transitions and assigns the selected reviewer.
- Prove a parent/cache rerender cannot start a duplicate autosave.
- Preserve reviewer queue links, draft submission, report visibility, and final
  admin decision tests.

## Boundaries

- Always: preserve backend authorization, immutable evidence, review audit data,
  keyboard accessibility, responsive layout, and existing theme support.
- Ask first: database migrations, new dependencies, CI changes, merge, deploy.
- Never: expose evidence to unauthorized roles, let admin author a reviewer
  report, let reviewer decide/sign, or silently discard a draft.

## Implementation plan

- [x] Stabilize draft persistence and add the duplicate-autosave regression.
- [x] Reduce admin intake to reviewer selection and assignment only.
- [x] Redesign reviewer queue and workspace information hierarchy.
- [x] Verify focused tests, quality gates, and production build.

## Success criteria

- Admin assignment detail contains no evidence viewer or evaluation textarea.
- A submitted dossier can be routed to an active reviewer in one visible action.
- Editing one reviewer field results in one settled autosave request.
- Reviewer queue and workspace communicate priority, status, deadline, evidence,
  progress, and next action without duplicated decorative panels.
