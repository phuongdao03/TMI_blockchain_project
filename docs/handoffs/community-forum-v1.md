# Community forum implementation handoff

## Delivered

- Added persisted topic follows, authenticated idempotent follow/unfollow, and a paginated `topics_following` feed while preserving member follows.
- Added the server-side `unanswered` feed sort. It counts only valid visible replies and keeps stable pagination.
- New replies notify eligible topic followers through the existing notification service, with self, post-author, reply-author, and mention recipients deduplicated.
- Added bounded plain-text reply quotes and a source-reply link in the reply composer.
- Wrapped category navigation to avoid horizontal scrolling on narrow screens.
- Preserved the current `/community`, `/community/posts/[slug]`, and `/community/new` routes and all existing post/comment data.

## Contracts and data

- `GET`, `PUT`, and `DELETE /api/v1/community/posts/{post_id}/follow` expose follow state and mutations.
- Community list `sort` now accepts `topics_following` and `unanswered`.
- Alembic revision `0158_community_post_follows` adds the unique `(post_id, user_id)` relation with cascading foreign keys and indexes. It has a downgrade. It was tested against an isolated SQLite database and was not applied to production.
- No payment, nomination, wallet, blockchain, membership chat, or account model changes.

## Verification

- Backend focused suites: 48 passed. Ruff: passed (`--no-cache`, because the sandbox denied `.ruff_cache` writes).
- Frontend community suites: 77 passed. ESLint: passed. `npx tsc --noEmit --incremental false`: passed.
- Next route type generation and production build could not run: sandbox `EPERM` blocked writes to `.next/types/routes.d.ts`, `tsconfig.json`, and an alternate `.next-*` build directory.
- No browser sessions were available for manual responsive inspection. No production migration or deployment was performed.

## Deferred

- Quote source links currently appear in the reply composer; persisting quote targets into published replies and quote-specific notifications remain unimplemented. Mention suggestions, accent-insensitive Vietnamese search, suspicious-link scanning, private-topic access rules, notification preferences, and queued/digest delivery also need a separate verified policy or infrastructure decision.
- Before release: run Next type generation/build in a writable environment; apply revision 0158 only through the reviewed deployment process; verify real authenticated notification journeys and narrow-device layouts.
