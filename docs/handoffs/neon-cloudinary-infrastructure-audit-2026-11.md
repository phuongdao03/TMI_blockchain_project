# Neon and Cloudinary infrastructure audit — November 2026

## Findings and evidence

- Invoice supplied for October: 362.260556 CU-hours and $38.40 compute out of $38.46 total. That is about 99.84% of this invoice. The monthly average is about 0.487 billed CU across 744 hours; it does not show active hours, compute size, or a cause.
- One read-only PostgreSQL snapshot against the configured pooled endpoint returned PostgreSQL 18.6, `max_connections=901`, three other idle sessions, zero idle-in-transaction sessions, `idle_in_transaction_session_timeout=300000`, `statement_timeout=0`, and no `pg_stat_statements` extension. The local environment selected `APP_ENV=local`; this is not identified as production and is not a history sample.
- `NEON_API_KEY` is not configured. Historical CU/active-time trends were unavailable. Neon Console Usage/Monitoring data is needed before changing pool sizing or attributing compute cost.
- Code review found Uvicorn with two workers and default SQLAlchemy pool sizing; the Celery worker uses `NullPool`. Several full-profile Beat jobs touch PostgreSQL every 5–60 seconds, including notification outbox polling every 5 seconds. This is a plausible source of repeated wakeups, not a measured cause. No pool or job cadence was changed without historical metrics.
- The database-only registry report for the configured local branch found 36 tracked Cloudinary keys, 13 `PENDING` media rows older than 48 hours, and 3 groups of repeated SHA-256 among active media. The latter two are review candidates, not proof of provider orphans or safe deletions.
- Cloudinary Admin inventory returned HTTP 420 on the first `image/authenticated` request in three single-request attempts. No provider asset counts were obtained. The script stops with the sanitized resource/type and status; do not treat the inventory as complete.

## Changes

- Added nullable unique `media_assets.upload_session_id` and an additive Alembic migration. Existing rows remain valid; the migration has not been applied to any database.
- Upload clients keep a UUID session ID for the queued file and reuse it after retry. Large chunked uploads also reuse that ID in `X-Unique-Upload-Id`.
- The API binds each session to its owner and exact intent. A retry returns the same media row and public ID. When a prior Cloudinary transfer succeeded but its response was lost, the backend checks provider metadata, moves a verified match into `QUARANTINED`, and queues the existing safety inspection. It does not skip inspection or change private-file handling.
- Certificate PDF retries use their existing deterministic public ID. If an upload response is ambiguous, the backend recovers only when the authenticated stored PDF has the expected metadata and its downloaded bytes hash exactly matches the rendered PDF.
- Added `backend/app/scripts/cloudinary_read_only_audit.py`. It reads the Neon registry and lists Cloudinary resources with Admin `GET` calls, caps requests at 100, defaults the review age to 48 hours (minimum 24), and can write age-qualified candidate IDs to a restricted report file. It has no deletion path. `--database-only` skips Cloudinary when the Admin API is rate limited.
- Added [`neon-read-only-audit.sql`](../../infrastructure/database/neon-read-only-audit.sql) for an administrative snapshot. It avoids SQL text and client IP output; the optional `pg_stat_statements` query is commented out and must not be enabled as part of this audit.

## Safe next steps

1. Apply migration `0159_media_upload_sessions` through the existing release process after review. It adds one nullable column and unique constraint; no production data rewrite or deletion is included.
2. In Neon Console, capture October compute/active-time/scale-to-zero and connection/query metrics, then compare with full-profile Beat schedules. Keep pool settings unchanged until that comparison is available.
3. Re-run the Cloudinary inventory after the account's Admin API rate limit clears. Review only a complete inventory. Verify each candidate in the Cloudinary Console and application references; there is no automatic delete command in this change.
4. Review stale pending rows and duplicate-hash groups using owner-authorized application workflows. Do not delete them solely from aggregate counts.

## External references

- [Neon scale to zero](https://neon.com/docs/guides/scale-to-zero-guide)
- [Neon usage monitoring](https://neon.com/docs/introduction/monitor-usage)
- [Neon monitoring page](https://neon.com/docs/introduction/monitoring-page)
- [Neon query performance and `pg_stat_statements`](https://neon.com/docs/introduction/monitor-query-performance)
- [Cloudinary Upload API](https://cloudinary.com/documentation/image_upload_api_reference)
- [Cloudinary Admin API](https://cloudinary.com/documentation/admin_api)
