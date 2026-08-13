import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("critical query plan collection is bounded, read-only and reproducible", async () => {
  const [queries, collector] = await Promise.all([
    read("infrastructure/database/critical-query-plans.sql"),
    read("infrastructure/scripts/collect-database-readiness.sh"),
  ]);

  assert.match(queries, /BEGIN READ ONLY/);
  assert.match(queries, /statement_timeout/);
  assert.match(queries, /EXPLAIN \(ANALYZE, BUFFERS, FORMAT JSON\)/g);
  for (const query of [
    "durable_job_queue",
    "public_verification",
    "audit_timeline",
    "public_search",
    "admin_certificate_queue",
  ]) {
    assert.ok(queries.includes(`readiness:${query}`), `missing query ${query}`);
  }
  assert.match(collector, /set -euo pipefail/);
  assert.match(collector, /DATABASE_DIRECT_URL/);
  assert.match(collector, /critical-query-plans\.sql/);
  assert.match(collector, /sha256sum/);
  assert.doesNotMatch(collector, /echo[^\n]*\$\{?DATABASE_DIRECT_URL/);
});

test("capacity policy names owners, budgets and online migration rules", async () => {
  const policy = await read(
    "docs/runbooks/database-capacity-and-migrations.md",
  );

  for (const phrase of [
    "Representative cardinality",
    "Query budget",
    "Growth threshold",
    "Retention",
    "Owner",
    "CREATE INDEX CONCURRENTLY",
    "NOT VALID",
    "VALIDATE CONSTRAINT",
    "rollback",
  ]) {
    assert.ok(policy.includes(phrase), `missing policy phrase: ${phrase}`);
  }
  assert.match(policy, /never run destructive cleanup automatically/i);
});

test("durable datastore signals have routes, thresholds and dashboard panels", async () => {
  const alerts = await read("infrastructure/monitoring/alert-policies.yaml");

  for (const signal of [
    "durable_job_oldest_queued_seconds",
    "durable_job_dead_lettered_count",
    "durable_job_retry_failure_count",
    "database_size_bytes",
  ]) {
    assert.ok(
      alerts.includes(`signal: ${signal}`),
      `missing alert for ${signal}`,
    );
    assert.ok(alerts.includes(signal), `missing dashboard panel for ${signal}`);
  }
});
