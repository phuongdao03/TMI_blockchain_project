# Public catalog cache runbook

## Design

Public list, featured, detail and taxonomy payloads use Redis keys scoped by a
schema version and monotonic generation. Public cache is never used by staff
preview. Writes use compare-generation semantics, so an old request cannot
repopulate a generation after invalidation. TTL is the fallback cleanup path.

Public-work and taxonomy outbox events increment the generation. The outbox poll
interval is five seconds; hide and suspend therefore target a five-second purge
SLA. Every list/detail cache hit is revalidated against current database
visibility/version, preventing hidden content disclosure during Redis races.
Redis errors fail open to database reads and emit structured warnings without
query values, descriptions, email addresses or other PII.

## Emergency purge

Inspect without mutation:

```powershell
python -m app.scripts.purge_public_catalog_cache
```

Invalidate all catalog scopes:

```powershell
python -m app.scripts.purge_public_catalog_cache --apply --reason "incident-id"
```

The command changes only the active generation. Old entries expire naturally; do
not use broad Redis deletion commands.

## Monitoring

The RBAC-protected operations response includes `publicCatalogCacheHitRatio` and
`publicCatalogCacheOperations`. Structured logs use
`public_catalog_cache_unavailable`, `public_catalog_cache_invalidated` and
`public_catalog_cache_invalidation_failed`. Alert when invalidation failures
continue beyond the configured catalog TTL or cache errors remain elevated.
