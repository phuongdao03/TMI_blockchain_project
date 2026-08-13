# Search discovery release gate

## Scope

This gate covers privacy-safe search events, trending snapshots, related works,
aggregate admin analytics, generation-scoped cache invalidation and public
search security/performance.

## Automated gate

Run from the repository root:

```powershell
python -m ruff check backend
cd backend
python -m mypy app
python -m pytest app/tests/test_full_text_search_repository.py app/tests/test_search_autocomplete.py app/tests/test_search_discovery.py app/tests/test_public_catalog_security_gate.py
```

The CI `public-security` job runs the same search visibility, bound-parameter,
autocomplete leakage, privacy and cache-stampede coverage. Any response that
contains owner, dossier or non-public work data blocks release.

## Migration gate

Migration `0021_search_discovery` must complete this sequence against PostgreSQL
17 before deployment:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Confirm that dashboard requests read `search_analytics_snapshots`; they must not
aggregate `search_events` in the request path.

## Query-plan regression

On a production-shaped staging dataset, capture
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for accented, unaccented, zero-result,
filtered and cursor-paginated searches. The public visibility predicate must be
present and the plan must use the search indexes described in
`search-index-foundation.md`. A sequential scan of `public_works` blocks
release.

## Load test

Install k6 0.54 or later, then run:

```bash
k6 run -e BASE_URL=https://staging.example/api/v1 tests/load/search-discovery.k6.js
```

Release thresholds are search P95 below 500 ms, autocomplete P95 below 250 ms
and HTTP failure rate below 1%. Run once with a cold cache, once warm, then hide
a published work during load. The hidden work must disappear within the cache
invalidation SLA and no stale-generation writer may restore it.

Record dataset cardinality, commit SHA, k6 summary, database CPU/IO, Redis hit
ratio and the JSON query plans in the release ticket. The gate remains open
until these staging artifacts exist; local or mocked results are not
substitutes.

## Incident controls

1. Disable trending and analytics workers if snapshot generation overloads the
   database; public search remains available.
2. Bump `public:catalog:v1:generation` through the normal outbox invalidator to
   evict result, autocomplete and related namespaces together.
3. Suppress a sensitive trending hash through the admin endpoint. Never inspect
   or log raw queries to identify it.
4. Roll back application code before downgrading the migration. Retain evidence
   required by the incident and privacy policies, then follow approved
   retention.
