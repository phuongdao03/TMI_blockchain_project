# Reviewer and admin decision lifecycle

## Objective

Make the submitted-dossier workflow explicit and operable end to end:

1. A super admin opens and prechecks a submitted dossier.
2. The super admin selects an active `MODERATOR` and assigns the locked version.
3. The reviewer receives a notification, reviews every document/video, and
   submits an immutable recommendation.
4. The super admin reads the reviewer report and records the authorized final
   decision.
5. An approved dossier enters the existing human blockchain-signing and
   publication workflow.

Reviewer recommendations are advisory. Reviewers cannot make a final dossier
decision or sign blockchain transactions.

## Commands

- Backend focused tests:
  `python -m pytest backend/app/tests/test_admin_review_queue_api.py backend/app/tests/test_review_assignment_api.py backend/app/tests/test_notification_delivery.py`
- Frontend focused tests:
  `npm --prefix frontend test -- --run frontend/src/components/admin/review-assignment-queue.test.tsx frontend/src/components/notifications/notification-presentation.test.ts`
- Format: `npm run format:check`
- Quality: `npm run lint && npm run typecheck`
- Build: `npm --prefix frontend run build`

## Project structure

- `backend/app/modules/reviews/`: assignment/report read model and commands.
- `backend/app/modules/council/`: final authorized decision and immutable
  minutes.
- `backend/app/workers/notification_tasks.py`: role-aware notification deep
  links.
- `frontend/src/components/admin/`: admin review queue, assignment, reports, and
  final-decision UI.
- `frontend/src/components/reviews/`: reviewer evidence and report workspace.
- `backend/app/tests/`, `frontend/src/**/*.test.tsx`: regression and contract
  tests.

## Code style

Contracts remain additive and camel-cased at the HTTP boundary:

```ts
interface AdminReviewAssignment {
  assignment: ReviewAssignment;
  reviewerEmail: string;
  review: ReviewData | null;
}
```

Use existing service/repository boundaries, semantic theme tokens, accessible
form labels, and focused components.

## Testing strategy

- Backend contract tests prove admin detail includes assignee identity and
  submitted reports.
- Service tests prove only active moderators can be assigned and only completed
  reports can reach final decision.
- Notification tests prove reviewer assignments open reviewer routes and
  completed reports open admin routes.
- Frontend tests prove precheck-and-assign is one guided action, reports are
  visible to admin, and final actions are gated.
- Existing review, council, blockchain, typecheck, formatting, and build checks
  guard regressions.

## Boundaries

- Always: preserve immutable dossier versions, authorization, audit history,
  evidence integrity checks, council decision records, and human wallet signing.
- Ask first: schema migrations, dependency additions, CI/deployment changes,
  merge, or production deployment.
- Never: let a reviewer self-assign, make the final decision, mutate evidence,
  or sign blockchain data; never expose private media publicly.

## Implementation plan

- [x] Add an admin assignment/report read contract and regression tests.
- [x] Present precheck and reviewer selection as one guided admin handoff.
- [x] Add a focused final-decision command that records the existing
      single-admin council controls atomically.
- [x] Show report details, decision readiness, and next blockchain step in the
      admin UI.
- [x] Correct role-aware notification links and verify the complete flow.

## Success criteria

- A submitted dossier is visible in the admin queue.
- Admin can read evidence, select an active reviewer, and complete precheck plus
  assignment without losing context.
- The selected reviewer sees the assignment and receives a working notification.
- A submitted reviewer report is visible in the same admin dossier screen.
- Admin cannot finalize before all assignments finish and explicitly declaring
  no conflict of interest; approval/rejection creates an auditable council
  record, while supplement requests reopen an editable evidence draft.
- Approval appears in the existing blockchain signer queue; publication still
  occurs only after the established signing/payment gates.
