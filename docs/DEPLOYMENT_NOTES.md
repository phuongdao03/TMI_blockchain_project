# Community deployment and rollback notes

Date: 2026-10-15. No production change has been made.

## Before rollout

- Confirm the release includes backend and frontend artifacts from the same revision.
- Back up the PostgreSQL database using the existing backup runbook.
- Verify media provider/scanner readiness. Set `COMMUNITY_POST_IMAGE_MAX_COUNT` and `COMMUNITY_POST_IMAGE_MAX_BYTES` for the backend and matching `NEXT_PUBLIC_COMMUNITY_POST_IMAGE_MAX_COUNT` and `NEXT_PUBLIC_COMMUNITY_POST_IMAGE_MAX_BYTES` for the frontend build. Defaults are 5 files and 5 MiB each; allowed ranges are 1–10 files and 1–20 MiB. Backend checks are authoritative.
- Confirm the initial moderation mode is `PRE_MODERATION`, the six categories are seeded idempotently, and the designated admins have `community.manage`/`community.moderate`.
- Review the migration plan, sitemap behavior, and `/cong-dong` redirect.

## Rollout

1. Apply the additive Alembic migration using the existing deployment runbook.
2. Deploy backend and frontend together; verify health/readiness, login, public `/community`, and admin moderation access.
3. Verify a draft/submit/approve flow, public detail, image inspection/delivery, report handling, and the existing nomination detail flow in a non-production environment.
4. Monitor API errors, upload inspection failures, moderation queue, and database query latency.

## Rollback

- First disable community entry points using the documented release configuration if the frontend/API must be rolled back independently.
- Roll back application artifacts using `docs/runbooks/deployment-and-rollback.md`.
- Downgrade the community migration only after confirming no retained community content must be exported; downgrade removes community-owned data. Do not drop or alter existing users, media, public works, notifications, or other application tables.
- A targeted rollback from migration `0109_community_admin_workspaces` to `0108_community_interactions` removes the new restriction table and post/comment columns but deliberately preserves the expanded moderation-event CHECK constraints. They must remain widened so retained COM012 audit rows stay valid; a full community teardown may remove the event table with the rest of community data.
- If content must be preserved, roll back code while leaving additive community tables in place, then repair forward.

## Known rollout limitations

- Community image limits are configurable. Backend and frontend values must match; changing `NEXT_PUBLIC_*` requires rebuilding the frontend.
- Removing a transferred upload from the pre-attachment queue deletes its media record/provider object. Removing an image already attached to a saved draft only detaches it; confirm the media retention/cleanup policy before operating at scale.
- Validate upload, moderation, sitemap, and published-work discussion journeys against a staging backend before production rollout; this workspace verification did not have a local API service available for browser end-to-end requests.
