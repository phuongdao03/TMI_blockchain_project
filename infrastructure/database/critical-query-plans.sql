\set ON_ERROR_STOP on

BEGIN READ ONLY;
SET LOCAL statement_timeout = '3s';
SET LOCAL lock_timeout = '500ms';
SET LOCAL idle_in_transaction_session_timeout = '15s';

-- readiness:cardinality
SELECT relname AS table_name, n_live_tup AS estimated_rows
FROM pg_stat_user_tables
WHERE relname IN (
  'job_executions',
  'certificates',
  'certificate_versions',
  'audit_logs',
  'public_works'
)
ORDER BY relname;

-- readiness:durable_job_queue
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, task_name, resource_type, resource_id, status, scheduled_at
FROM job_executions
WHERE status IN ('QUEUED', 'DEAD_LETTERED')
ORDER BY scheduled_at ASC, id ASC
LIMIT 20;

-- readiness:public_verification
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, certificate_number, status, current_version_no
FROM certificates
WHERE certificate_number = 'TMI-READINESS-SENTINEL'
LIMIT 1;

-- readiness:audit_timeline
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, actor_user_id, action, resource_type, resource_id, created_at
FROM audit_logs
WHERE resource_type = 'dossier'
ORDER BY created_at DESC, id DESC
LIMIT 50;

-- readiness:public_search
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, slug, title, published_at
FROM public_works
WHERE publication_status = 'PUBLISHED'
  AND visibility = 'PUBLIC'
  AND search_vector @@ websearch_to_tsquery('simple', 'tmi')
ORDER BY published_at DESC, id ASC
LIMIT 21;

-- readiness:admin_certificate_queue
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, certificate_id, status, requested_at
FROM certificate_versions
WHERE status IN ('PENDING_APPROVAL', 'ANCHOR_PENDING', 'FAILED')
ORDER BY requested_at ASC, id ASC
LIMIT 20;

ROLLBACK;
