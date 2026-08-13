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
  const [compose, productionEnvironment] = await Promise.all([
    read("infrastructure/compose.production.yaml"),
    read("infrastructure/.env.production.example"),
  ]);
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
  assert.match(frontendService, /API_BASE_URL: http:\/\/backend:8000/);
  assert.doesNotMatch(frontendService, /NEXT_PUBLIC_PREVIEW_MODE/);
  assert.match(compose, /worker:[\s\S]*?healthcheck:/);
  assert.match(compose, /scheduler:[\s\S]*?healthcheck:/);
  assert.doesNotMatch(
    compose,
    /BLOCKCHAIN_SIGNER_PRIVATE_KEY|\.key:\/|\.pem:\//,
  );
  assert.doesNotMatch(productionEnvironment, /BLOCKCHAIN_SIGNER_PRIVATE_KEY/);
  assert.match(productionEnvironment, /^BLOCKCHAIN_SIGNER_MODE=managed$/m);
});

test("nginx production config enforces TLS, headers and webhook isolation", async () => {
  const nginx = await read("infrastructure/nginx/production.conf.template");

  assert.match(nginx, /ssl_protocols TLSv1\.2 TLSv1\.3/);
  assert.match(nginx, /Strict-Transport-Security/);
  assert.match(nginx, /Content-Security-Policy/);
  assert.match(
    nginx,
    /location = \/health[\s\S]*?proxy_pass http:\/\/backend_upstream\/health/,
  );
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
  assert.match(workflow, /STAGING_SSH_KNOWN_HOSTS/);
  assert.match(workflow, /PRODUCTION_SSH_KNOWN_HOSTS/);
  assert.match(workflow, /GHCR_PULL_TOKEN/);
  assert.match(workflow, /StrictHostKeyChecking=yes/);
  assert.match(workflow, /rsync -az/);

  const foundryImage = "ghcr.io/foundry-rs/foundry:v1.7.1";
  for (const command of [
    "fmt --check",
    "build --force",
    "test --fuzz-runs 256",
  ]) {
    assert.match(
      workflow,
      new RegExp(
        `docker run [^\\n]*--entrypoint forge [^\\n]*${foundryImage.replaceAll(".", "\\.")} ${command.replaceAll("-", "\\-")}`,
      ),
      `CI must invoke the pinned image through the forge entrypoint: ${command}`,
    );
  }
});

test("deployment scripts wait for healthy services and preserve an image rollback path", async () => {
  const [deploy, rollback, releaseLibrary, rollbackWorkflow] =
    await Promise.all([
      read("infrastructure/scripts/deploy.sh"),
      read("infrastructure/scripts/rollback.sh"),
      read("infrastructure/scripts/release-lib.sh"),
      read(".github/workflows/rollback.yml"),
    ]);

  for (const script of [deploy, rollback]) {
    assert.match(script, /flock/);
    assert.match(script, /previous-image-tag/);
  }
  assert.match(releaseLibrary, /--wait-timeout/);
  assert.match(deploy, /AUTO_ROLLBACK_ON_FAILURE/);
  assert.match(rollbackWorkflow, /workflow_dispatch:/);
  assert.match(rollbackWorkflow, /GHCR_PULL_TOKEN/);
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
    "auth_failure_spike",
    "redis_unavailable",
    "payment_webhook_failure",
    "certificate_issuance_failure",
    "blockchain_pending_age",
    "wallet_balance",
    "blockchain_rpc_outage",
    "blockchain_stuck_nonce",
    "blockchain_reverted_transaction",
    "blockchain_state_mismatch",
    "backup_freshness",
  ]) {
    assert.ok(alerts.includes(signal), `missing alert signal: ${signal}`);
  }
  assert.match(incident, /SEV-1/);
  assert.match(incident, /rollback/i);
  assert.match(recovery, /RPO/);
  assert.match(recovery, /RTO/);
  assert.match(recovery, /restore drill/i);
  assert.match(recovery, /Redis-loss recovery/i);
});

test("Amoy release gate is fail-closed and publishes explorer evidence", async () => {
  const [script, stagingEnvironment, runbook] = await Promise.all([
    read("infrastructure/scripts/deploy-contract-amoy.sh"),
    read("infrastructure/.env.staging.example"),
    read("docs/runbooks/blockchain-release.md"),
  ]);

  assert.match(script, /set -euo pipefail/);
  assert.match(script, /chain_id[^\n]*80002|80002[^\n]*chain_id/);
  assert.match(script, /cast wallet address/);
  assert.match(script, /EXPECTED_DEPLOYER/);
  assert.match(script, /forge script/);
  assert.match(script, /export-artifacts\.mjs/);
  assert.match(script, /forge verify-contract/);
  assert.match(script, /record-explorer-evidence\.mjs/);
  assert.doesNotMatch(script, /echo[^\n]*DEPLOYER_PRIVATE_KEY/);

  assert.match(stagingEnvironment, /^APP_ENV=staging$/m);
  assert.match(stagingEnvironment, /^BLOCKCHAIN_NETWORK=amoy$/m);
  assert.match(stagingEnvironment, /^BLOCKCHAIN_CHAIN_ID=80002$/m);
  assert.match(
    stagingEnvironment,
    /^BLOCKCHAIN_EXPLORER_BASE_URL=https:\/\/amoy\.polygonscan\.com$/m,
  );
  assert.match(runbook, /explorer-evidence\.json/);
  assert.match(runbook, /never commit/i);
});

test("Polygon production contract gate is read-only and approval protected", async () => {
  const [workflow, preflight, runbook, incident] = await Promise.all([
    read(".github/workflows/contract-release.yml"),
    read("infrastructure/scripts/blockchain-preflight.sh"),
    read("docs/runbooks/blockchain-release.md"),
    read("docs/runbooks/incident-response.md"),
  ]);

  assert.match(workflow, /workflow_dispatch:/);
  assert.match(workflow, /environment: production-blockchain/);
  assert.match(workflow, /ref: \$\{\{ inputs\.source_commit \}\}/);
  assert.match(workflow, /blockchain-preflight\.sh/);
  assert.match(workflow, /production-release-plan\.mjs/);
  assert.doesNotMatch(workflow, /forge script[^\n]*--broadcast/);

  assert.match(preflight, /set -euo pipefail/);
  assert.match(preflight, /https:\/\//);
  assert.match(preflight, /chain_id[^\n]*137|137[^\n]*chain_id/);
  assert.match(preflight, /cast balance/);
  assert.match(preflight, /runtime_bytecode/i);
  assert.match(preflight, /hasRole/);
  assert.match(preflight, /BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES/);
  assert.match(runbook, /canary/i);
  assert.match(runbook, /pause/i);
  assert.match(incident, /pause/i);
});
