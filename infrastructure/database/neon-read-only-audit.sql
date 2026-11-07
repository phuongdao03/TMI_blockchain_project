-- Read-only Neon snapshot. Run as an administrative/read-only role.
BEGIN READ ONLY;

SELECT now() AS sampled_at,
       current_database() AS database_name,
       current_setting('server_version') AS server_version;

SELECT name, setting, unit
FROM pg_settings
WHERE name IN (
  'max_connections',
  'idle_in_transaction_session_timeout',
  'idle_session_timeout',
  'statement_timeout'
)
ORDER BY name;

-- Group only; do not expose live SQL text or client addresses in audit output.
SELECT coalesce(application_name, '') AS application_name,
       state,
       count(*) AS connections,
       max(now() - state_change) AS oldest_state_age
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
GROUP BY coalesce(application_name, ''), state
ORDER BY connections DESC, application_name, state;

SELECT count(*) AS idle_in_transaction_connections
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
  AND state LIKE 'idle in transaction%';

SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size,
       pg_database_size(current_database()) AS database_size_bytes;

SELECT to_regclass('public.pg_stat_statements') IS NOT NULL
       AS pg_stat_statements_available;

-- If available and permitted, run this query separately to avoid failing the
-- read-only checklist when the extension is absent or access is restricted:
-- SELECT queryid, calls, total_exec_time, mean_exec_time, rows,
--        shared_blks_hit, shared_blks_read, temp_blks_written
-- FROM pg_stat_statements
-- ORDER BY total_exec_time DESC
-- LIMIT 20;

-- One snapshot does not provide Neon CU-hours, scale-to-zero history, or a
-- time series. Read those in the Neon Console Usage and Monitoring pages.
ROLLBACK;
