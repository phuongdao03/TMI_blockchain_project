# Database capacity and safe migrations

This runbook defines the repeatable evidence gate for PostgreSQL. It does not
claim that staging or production has passed until the generated evidence is
attached to a release ticket and independently reviewed.

## Representative cardinality and query budget

Run `infrastructure/scripts/collect-database-readiness.sh <evidence-directory>`
against an isolated staging database containing production-shaped, sanitized
data. Keep the generated directory encrypted and access logged. Never include a
connection URL, query parameter containing personal data, or raw private
document metadata in the ticket.

| Workload                |               Representative cardinality | Query budget (P95) |                        Growth threshold | Owner                   |
| ----------------------- | ---------------------------------------: | -----------------: | --------------------------------------: | ----------------------- |
| Durable job queue       | 1 million executions, 5 million attempts |             150 ms |  oldest queued > 300 s or table > 20 GB | Platform                |
| Public verification     |      5 million certificates and versions |             100 ms |                 P95 > 100 ms for 15 min | Certificate operations  |
| Audit timeline          |            50 million append-only events |             300 ms | primary table > 100 GB or index > 40 GB | Security and compliance |
| Public search           |                2 million published works |             400 ms |      P95 > 400 ms or timeout ratio > 1% | Search and platform     |
| Admin certificate queue |           1 million certificate versions |             200 ms |             pending queue > 10,000 rows | Certificate operations  |

The gate passes when every plan stays inside its Query budget, uses an intended
index for a non-trivial result set, avoids unexpected sequential scans on the
largest relations, and reports no temporary-file spill. A plan captured against
materially smaller data is diagnostic only, not production readiness evidence.

## Production-shaped API load

The operational k6 profile exercises liveness, readiness, public catalog and a
known public certificate. Use only sanitized seeded data. Non-local execution
fails closed unless the target is HTTPS and staging approval is explicit:

```bash
k6 run \
  -e BASE_URL=https://staging.example \
  -e LOAD_ENVIRONMENT=staging \
  -e STAGING_READINESS_APPROVED=1 \
  -e VERIFY_CERTIFICATE_NUMBER=TMI-STAGING-SENTINEL \
  tests/load/operational-readiness.k6.js
```

Attach the k6 summary, dataset cardinality, image tag, query-plan bundle and
database/Redis resource graphs to the change ticket. A local run is diagnostic
only and must not be presented as staging or production evidence.

## Index review

For each plan, record actual rows, total execution time, shared hit/read blocks,
temporary blocks and the selected index. Propose an index only when the plan and
cardinality demonstrate need. Record write amplification and index size before
approval. Do not add overlapping indexes based only on a local SQLite plan.

## Retention and archive thresholds

| Data                         | Retention                                   | Archive/cleanup gate                                      | Owner                   |
| ---------------------------- | ------------------------------------------- | --------------------------------------------------------- | ----------------------- |
| Audit events                 | Seven years unless legal hold applies       | encrypted immutable archive after compliance approval     | Security and compliance |
| Durable job attempts         | 400 days after terminal state               | aggregate metrics first; retain job intent and audit link | Platform                |
| Search history               | Configured consent window, maximum 365 days | scheduled privacy purge with deletion count only          | Privacy owner           |
| Request/application logs     | 90 days hot, 365 days encrypted archive     | redact before export                                      | Platform and security   |
| Redis cache/rate-limit state | Operational TTL only                        | rebuild from PostgreSQL; never restore as business truth  | Platform                |

Never run destructive cleanup automatically merely because a Growth threshold
was crossed. Open a reviewed change, check legal holds, take a fresh backup,
verify the archive checksum, then execute a bounded batch job with pause and
rollback controls.

## Safe online migration rules

1. Prefer additive, backward-compatible expand/migrate/contract releases.
2. Set `lock_timeout` and `statement_timeout`; never wait indefinitely for a
   production table lock.
3. Build large PostgreSQL indexes with `CREATE INDEX CONCURRENTLY`. Because it
   cannot run inside Alembic's normal transaction, use an explicit autocommit
   block and verify/remove an invalid index before retrying.
4. Add expensive checks or foreign keys as `NOT VALID`, backfill in bounded
   resumable batches, then run `VALIDATE CONSTRAINT` separately.
5. Add nullable columns or safe server defaults first. Enforce `NOT NULL` only
   after backfill and validation.
6. Never combine destructive column/table removal with the release that stops
   writing it. Keep at least one rollback-compatible release window.
7. Capture before/after query plans, lock duration, replica lag and error rate.
   Stop when a budget or alert threshold is exceeded.

## Rollback and evidence

Before execution, record the immutable image tag, Alembic revision, backup/PITR
status, migration owner and rollback decision point. Schema rollback must not
discard data written by the new version. If downgrade is unsafe, roll the
application forward with a compatibility migration instead. Store
`query-plans.txt`, `database-summary.json` and `manifest.sha256` with the
release record; an independent reviewer verifies the checksum and signs the
ticket.
