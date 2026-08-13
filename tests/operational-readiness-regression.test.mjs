import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import test from "node:test";

const exec = promisify(execFile);
const root = new URL("../", import.meta.url);
const read = (path) => readFile(new URL(path, root), "utf8");

test("operational load covers liveness, readiness, catalog and verification", async () => {
  const load = await read("tests/load/operational-readiness.k6.js");

  for (const endpoint of [
    "/health",
    "/ready",
    "/public/home",
    "/public/works",
    "/verify/certificate/",
  ]) {
    assert.ok(load.includes(endpoint), `missing load endpoint: ${endpoint}`);
  }
  assert.match(load, /VERIFY_CERTIFICATE_NUMBER/);
  assert.match(load, /p\(95\)</);
  assert.match(load, /STAGING_READINESS_APPROVED/);
  assert.match(load, /https:/);
});

test("regression runner declares dependency failures as simulation evidence", async () => {
  const runner = fileURLToPath(
    new URL(
      "infrastructure/scripts/run-operational-readiness-regressions.mjs",
      root,
    ),
  );
  const result = await exec(process.execPath, [runner, "--list"]);
  const plan = JSON.parse(result.stdout);

  assert.equal(plan.schemaVersion, 1);
  assert.equal(plan.evidenceClass, "simulation_only");
  assert.deepEqual(
    plan.scenarios.map((scenario) => scenario.id),
    ["database", "redis", "blockchain_rpc"],
  );
  assert.ok(
    plan.scenarios.every(
      (scenario) =>
        scenario.command === "python" &&
        scenario.arguments[0] === "-m" &&
        scenario.arguments[1] === "pytest",
    ),
  );
});

test("CI retains the operational regression artifact without calling it a staging drill", async () => {
  const workflow = await read(".github/workflows/delivery.yml");

  assert.match(workflow, /operational-readiness:/);
  assert.match(workflow, /run-operational-readiness-regressions\.mjs/);
  assert.match(workflow, /operational-readiness-regression-/);
  assert.match(workflow, /retention-days: 14/);
});
