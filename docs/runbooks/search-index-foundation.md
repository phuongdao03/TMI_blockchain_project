# Search index foundation runbook

## Migration behavior

Migration `0018_search_foundation` enables `unaccent` and `pg_trgm`, then adds
three relation-derived helper fields and a weighted `search_vector` to
`public_works`. A trigger weights title/certificate as A,
author/organization/taxonomy as B, and descriptions as C. The initial backfill
uses batches of 1,000 rows with `SKIP LOCKED` and never changes publication
status or visibility.

GIN full-text and trigram indexes are partial: only non-deleted `PUBLISHED +
PUBLIC` rows are index candidates. Indexes are built concurrently in an Alembic
autocommit block. The visibility/published/id B-tree supports stable tie-breaks.

## Pre-deploy

1. Confirm the deployment role can create extensions and concurrent indexes.
2. Record table size, current lock activity and free disk capacity.
3. Run migration on a production-shaped staging snapshot and watch lock waits,
   replica lag and index build progress.
4. Do not enable search APIs until migration, visibility, query-plan and load
   gates pass.

## Query-plan evidence

On staging, run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for representative
accented/unaccented full-text and trigram queries while applying the exact
`PUBLISHED`, `PUBLIC`, `deleted_at IS NULL` predicate. Attach the JSON plan and
dataset cardinality to the release ticket. Expected nodes use
`ix_public_works_search_vector_public` or the appropriate trigram bitmap index;
a sequential scan on the target dataset blocks release.

## Rollback

Downgrade removes the trigger, helper/vector columns and search indexes. It
intentionally retains `unaccent` and `pg_trgm` because extensions may be shared
by other database objects. Extension removal requires a separately reviewed
dependency audit; never drop them as part of an incident rollback.
