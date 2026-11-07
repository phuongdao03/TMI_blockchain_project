# Community forum master prompt audit — 2026-11

## Scope and assumptions

- Treat existing community posts as topics and comments as replies; do not create a parallel forum/account system.
- Keep the platform's session, roles, membership, notification center, media service, and existing public routes authoritative.
- Keep the first release public-only. Do not introduce private-topic visibility without a separate access and indexing policy.
- Preserve existing posts, comments, tags, moderation history, chat, and unrelated payment, nomination, wallet, and blockchain flows.
- Any schema work is additive and reversible. Do not run migrations against production.

## Current state

| Area | Existing implementation |
| --- | --- |
| Frontend | `/community`, post detail, new post, member profile, saved posts, and My Posts; shared public shell, theme tokens, loading/error/empty states, search, category filter, URL state, and server pagination. |
| Backend/data | FastAPI community endpoints and existing post/category/comment/profile/reaction/bookmark/member-follow/report/moderation models; Alembic migrations through the current community work; visibility filters, bounded validation, CSRF-protected writes, rate limits, inspected image delivery, and notification transactions. |
| Discussion | Replies and mentions are supported. Replies retain parent references and are displayed as a bounded flat conversation. |
| Community features | Member follows, likes, bookmarks, member directory/profile, membership-derived badges, event registration, and member chat access reuse existing platform systems. |
| Moderation | Reports, moderator-only queue and resolution, reversible hide/restore, pin/lock, restrictions, audit events, and author notifications are implemented. |

## Verified gaps

1. **Topic follow is absent.** Existing `CommunityFollow` is person-to-person; `/community?sort=following` shows posts from followed authors. It does not subscribe to a particular discussion or notify a subscriber about replies.
2. **Unanswered filter is absent.** Feed sorting supports recent, popular, discussed, and followed authors, but not zero-reply topics.
3. **Reply quoting is incomplete.** Reply composers support parent replies but do not prefill a bounded quote or link back to the quoted reply.
4. **Mobile category navigation can overflow horizontally.** The feed uses a horizontally scrolling category strip where the prompt asks for a mobile layout without unintended horizontal scrolling.
5. **Mention autocomplete is absent.** The backend resolves existing `@username` mentions and sends notifications; the editor has no suggestions.

## Reuse, risks, and data preservation

- Reuse `community_posts`, `community_comments`, the existing notification service, account identity, moderation, and existing UI/API envelopes.
- A distinct post-follow association is required because member-follow rows have different semantics. Use a unique `(post_id, user_id)` constraint and indexes; do not reinterpret existing rows.
- Keep follow/unfollow idempotent and authenticated. Notify the post author, reply author, and mentions at most once per reply; skip the reply author and recipients already notified for that reply.
- Keep quote content as escaped/plain text and use the existing comment parent reference for a stable reply link. Do not render user quote text as HTML.
- Leave legacy content and tag data untouched. New feed filters must run in the backend and remain paginated.
- Existing notification writes are transactional; a large subscriber fan-out can increase reply latency. Measure and consider queued/digest delivery if topic volume warrants it.
- Private topics, full-text Vietnamese search, suspicious-link policy, and notification preferences need separate verification or product policy before schema/behavior expansion.

## Feature spec

### Objective and success criteria

Complete the most visible forum gaps on the existing community module. A signed-in member can follow a discussion, return to followed discussions, and get a notification when someone replies. Any visitor can filter to unanswered topics. Members can quote a reply with a bounded text excerpt and navigate to its source. The mobile feed has no unintended horizontal overflow.

Success means these actions use persisted backend data, server pagination, existing session/RBAC/notification infrastructure, and safe text rendering; API behavior is covered by backend tests and the visible flows by frontend tests.

### Stack and project structure

- Frontend: Next.js 16.4.3 App Router, React 19.2.8, TypeScript, TanStack Query, Vitest.
- Backend: FastAPI, SQLAlchemy async, PostgreSQL-compatible models, Alembic, pytest.
- Frontend source: `frontend/src/app/(public)/community`, `frontend/src/components/community`, and `frontend/src/lib/api`.
- Backend source: `backend/app/api/v1/community*.py`, `backend/app/modules/community`, and `backend/alembic/versions`.

### Commands

- Backend focused: `python -m pytest app/tests/test_community_api.py app/tests/test_community_migration.py -q --tb=short` from `backend`.
- Frontend focused: `npm test -- --run src/components/community` from `frontend`.
- Frontend checks: `npm run typecheck`, `npm run lint`, `npm run build` from `frontend`.

### Code style and API contract

Keep the API additive and follow existing snake_case model fields, camelCase JSON DTOs, `SuccessEnvelope`/paginated envelopes, service/repository boundaries, and query-key conventions. For example:

```python
@router.put("/posts/{post_id}/follow")
async def follow_post(post_id: UUID, principal: CsrfProtectedPrincipalDependency):
    return SuccessEnvelope(data=await service.set_post_follow(principal, post_id, True))
```

The final handler must use the existing dependencies, response metadata, typed schema, transaction, and error envelope conventions. Never trust a client-supplied user ID or role.

### Testing strategy

Test idempotent follow/unfollow, ownership/visibility checks, pagination, notification deduplication/recipients, unanswered ordering, quote truncation/source links, and mobile feed controls. Test migration upgrade/downgrade on the repository's isolated test database. Run only the requested focused suites first, then the listed quality gates; report commands that cannot run.

### Boundaries

- Always: preserve existing post/comment rows and current member-follow semantics; authorize writes server-side; use the existing platform identity, membership, media, and notification systems; keep quotes as text.
- Ask before: destructive migration, production migration/data changes, private-topic access semantics, new dependencies, or external notification/search integrations.
- Never: create a second account/role system, expose private moderation state publicly, render quote text as HTML, or alter payment, nomination, wallet, chat, or blockchain workflows.

### Open questions

- Should topic notifications become digest/queued delivery if subscriber counts create measurable reply latency? Start with current transaction conventions and measure before adding infrastructure.
- Private topics, Vietnamese accent-insensitive full-text search, and suspicious-link policy are outside this implementation slice and require separate verified requirements.

## Implementation plan

1. Add topic-follow storage/API and focused backend tests using an additive rollback-capable migration.
2. Add follow state/action and a paginated followed-topic feed; keep member-follow behavior and labels distinct.
3. Add the unanswered server-side sort and matching URL/UI state.
4. Add a bounded quote action with a link to the referenced reply; keep comment rendering text-safe.
5. Remove unintended horizontal overflow in mobile category navigation and cover the feed states with frontend tests.
6. Run focused backend/frontend tests, lint/typecheck/build as available, review the diff, and update the handoff. Production rollout and migration application remain out of scope.

### Task breakdown

- [x] **T1 — Topic-follow schema:** add a unique post/member relation and reversible migration; prove upgrade/downgrade on isolated test data. Files: model, migration, migration test.
- [x] **T2 — Topic-follow API and notices:** add authenticated idempotent follow/unfollow, paginated followed-topic query, and one reply notice per eligible follower; preserve author/mention deduplication. Files: repository, service, schema, API, backend API tests.
- [x] **T3 — Follow UI:** show current follow state on topic detail and expose a distinct followed-topic filter with login return; preserve member-follow filter semantics. Files: API client/types, action/feed UI, focused component tests.
- [x] **T4 — Unanswered query:** filter zero-reply published topics with stable pagination. Files: backend route, repository, API tests.
- [x] **T5 — Unanswered feed state:** add the query parameter, label, URL retention, and login behavior where needed. Files: frontend API types/client, feed, component tests.
- [x] **T6 — Quote reply:** prefill a reply with a bounded plain-text excerpt, expose a link to the source reply, and cover the behavior with focused component tests. Files: quote helper, component, tests.
- [x] **T7 — Mobile feed and review:** wrap category controls at narrow widths; run focused checks and configured static gates; update handoff and report deferred items. Files: feed component/test, handoff.

## Verification commands

- Backend: `python -m pytest app/tests/test_community_api.py app/tests/test_community_migration.py -q --tb=short` (from `backend`).
- Frontend: `npm test -- --run src/components/community` (from `frontend`), followed by `npm run typecheck`, `npm run lint`, and `npm run build` after source changes.
- Migration tests use the repository's isolated test database setup; never point them at production.


## Implementation and verification outcome

Tasks T1-T7 are complete. Topic follows, unanswered sorting, reply quoting, and wrapped mobile category controls use the existing forum and platform services. The detailed implementation and release handoff is in [community-forum-v1.md](handoffs/community-forum-v1.md).

Focused backend suites: 48 passed. Focused frontend community suites: 77 passed. Ruff and ESLint passed; direct TypeScript compilation passed. Next route type generation and production build were blocked by sandbox `EPERM` on generated output/config paths. Manual browser inspection was unavailable because no browser session was connected.

The migration is additive/reversible and tested only against isolated SQLite test data. It is not applied to production. Deferred items remain mention suggestions, Vietnamese accent-insensitive search, suspicious-link scanning, private-topic policy, notification preferences, quote-specific notices, and queued/digest notices.
