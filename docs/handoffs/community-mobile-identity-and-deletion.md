# Community mobile, identity, and deletion handoff

## Requirements

- Feed previews stay short and link to the full article through **Xem thêm**.
- Signed-in users without a public display name see a persistent setup prompt;
  new signups are told to set it after verification.
- Community comments, feed controls, and member cards use tighter mobile
  spacing.
- Deleting a post removes its comments, reactions, reports, notifications,
  moderation history, attached image files, Cloudinary backup versions, and
  image metadata. Keep one content-free deletion event.
- Existing soft-deleted posts are purged by the community retention worker.

## Implementation

- The public and dashboard shells share the display-name reminder, which
  disappears after the profile query updates.
- Owner and moderator deletion use the media gateway, then remove post data and
  owned community image rows in the same final database transaction.
- A Celery beat task runs every five minutes. It purges one legacy deleted post
  and one orphaned, already-deleted community image row per run, including
  Cloudinary backup versions when asset IDs are available. The small batch
  limits protect Cloudinary's rate-limited Admin API.
- Admin deletion is permanent. Hidden posts can still be restored to public
  visibility; deleted posts cannot be restored.
- No schema migration is required.

## Operations

- Deploy the API and the Celery worker/beat processes together so existing
  soft-deleted posts are cleaned after rollout.
- Trigger an immediate sweep with
  `docker compose exec worker celery --app app.workers.celery_app call app.workers.community_retention_tasks.purge_deleted_community_media`.
- Cloudinary deletion failures leave the post and media metadata available for
  another scheduled attempt.
- The retention worker skips deleted-media metadata that remains referenced by a
  post or profile.

## Verification

- Frontend: 13 focused Vitest tests passed; frontend TypeScript check passed.
- Backend deletion and backup regression tests: 4 passed.
- Frontend ESLint, Ruff, Prettier, and `git diff --check` passed.
- Backend mypy could not start because its SQLite cache could not be opened in
  this environment.
