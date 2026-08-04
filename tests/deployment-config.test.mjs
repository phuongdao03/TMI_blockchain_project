import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("production images are multi-stage, non-root and health checked", async () => {
  const [backend, frontend] = await Promise.all([
    read("backend/Dockerfile"),
    read("frontend/Dockerfile"),
  ]);

  for (const dockerfile of [backend, frontend]) {
    assert.match(dockerfile, /FROM .+ AS .+/);
    assert.match(dockerfile, /USER \d+|USER (?:app|node)/);
    assert.match(dockerfile, /HEALTHCHECK/);
    assert.doesNotMatch(dockerfile, /latest/);
  }
  assert.match(frontend, /standalone/);
});

test("production compose exposes only TLS proxy and uses versioned images", async () => {
  const compose = await read("infrastructure/compose.production.yaml");
  const frontendService = compose.match(
    /\n  frontend:\n([\s\S]*?)\n  worker:/,
  )?.[1];

  assert.match(compose, /IMAGE_TAG/);
  assert.match(compose, /"80:8080"/);
  assert.match(compose, /"443:8443"/);
  assert.doesNotMatch(compose, /"(?:3000|8000|6379):/);
  assert.match(compose, /read_only: true/g);
  assert.match(compose, /restart: unless-stopped/g);
  assert.ok(frontendService, "frontend service is missing");
  assert.doesNotMatch(frontendService, /env_file:/);
});

test("nginx production config enforces TLS, headers and webhook isolation", async () => {
  const nginx = await read("infrastructure/nginx/production.conf.template");

  assert.match(nginx, /ssl_protocols TLSv1\.2 TLSv1\.3/);
  assert.match(nginx, /Strict-Transport-Security/);
  assert.match(nginx, /Content-Security-Policy/);
  assert.match(nginx, /location \/api\/v1\/webhooks\/payments\//);
  assert.match(nginx, /limit_req/);
});

test("CI has quality, migration, image, staging and manual production gates", async () => {
  const workflow = await read(".github/workflows/delivery.yml");

  for (const gate of [
    "quality:",
    "migration:",
    "images:",
    "deploy-staging:",
    "deploy-production:",
    "npm audit --audit-level=high",
    "npm --prefix frontend ci",
    "npm --prefix contracts ci",
    "frontend/node_modules/.bin/playwright install --with-deps chromium",
    "aquasec/trivy:0.68.2",
  ]) {
    assert.ok(workflow.includes(gate), `missing delivery gate: ${gate}`);
  }
  assert.match(workflow, /environment: production/);
  assert.match(workflow, /workflow_dispatch:/);
});

test("monitoring and recovery configs contain actionable signals", async () => {
  const [alerts, incident, recovery] = await Promise.all([
    read("infrastructure/monitoring/alert-policies.yaml"),
    read("docs/runbooks/incident-response.md"),
    read("docs/runbooks/backup-and-restore.md"),
  ]);

  for (const signal of [
    "api_error_rate",
    "queue_backlog",
    "database_pool_exhaustion",
    "payment_webhook_failure",
    "blockchain_pending_age",
    "wallet_balance",
  ]) {
    assert.ok(alerts.includes(signal), `missing alert signal: ${signal}`);
  }
  assert.match(incident, /SEV-1/);
  assert.match(incident, /rollback/i);
  assert.match(recovery, /RPO/);
  assert.match(recovery, /RTO/);
  assert.match(recovery, /restore drill/i);
});
