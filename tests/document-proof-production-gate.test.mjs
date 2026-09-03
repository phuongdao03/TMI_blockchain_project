import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  createDocumentProofEvidence,
  documentProofScenarios,
  validateDocumentProofEvidence,
} from "../infrastructure/scripts/run-document-proof-production-gate.mjs";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("document proof gate covers every production-risk category", () => {
  assert.deepEqual(
    documentProofScenarios.map(({ id }) => id),
    [
      "migrations",
      "encryption_and_key_rotation",
      "storage_and_delivery",
      "claims_and_authorization",
      "proof_registry_reliability",
      "verification_and_leakage",
      "frontend_verification",
      "verification_e2e",
      "thv_proof_registry_contract",
    ],
  );
  assert.ok(
    documentProofScenarios.every(
      ({ command, arguments: args }) =>
        typeof command === "string" &&
        command.length > 0 &&
        Array.isArray(args) &&
        args.length > 0,
    ),
  );
});

test("frontend scenario uses the platform executable without a shell", () => {
  const frontend = documentProofScenarios.find(
    ({ id }) => id === "frontend_verification",
  );

  assert.equal(
    frontend.command,
    process.platform === "win32" ? process.execPath : "npm",
  );
  if (process.platform === "win32") {
    assert.match(frontend.arguments[0], /npm-cli\.js$/);
  }
});

test("document proof evidence is bounded, redacted and fail closed", () => {
  const evidence = createDocumentProofEvidence({
    environment: "ci",
    sourceRevision: "a".repeat(40),
    startedAt: "2026-08-12T01:00:00.000Z",
    finishedAt: "2026-08-12T01:01:00.000Z",
    results: documentProofScenarios.map(({ id }, index) => ({
      id,
      exitCode: index === 4 ? 1 : 0,
      durationMs: 10 + index,
    })),
  });

  assert.equal(evidence.status, "FAIL");
  assert.equal(evidence.releaseScope, "document_proof_only");
  assert.deepEqual(Object.keys(evidence.results[0]).sort(), [
    "durationMs",
    "exitCode",
    "id",
  ]);
  assert.doesNotMatch(
    JSON.stringify(evidence),
    /stdout|stderr|secret|private.?key/i,
  );
  assert.doesNotThrow(() => validateDocumentProofEvidence(evidence));
});

test("document proof evidence rejects missing, duplicate and dishonest results", () => {
  const passingResults = documentProofScenarios.map(({ id }) => ({
    id,
    exitCode: 0,
    durationMs: 1,
  }));
  const base = {
    environment: "local",
    sourceRevision: "local-working-tree",
    startedAt: "2026-08-12T01:00:00.000Z",
    finishedAt: "2026-08-12T01:01:00.000Z",
    results: passingResults,
  };

  const passing = createDocumentProofEvidence(base);
  assert.equal(passing.status, "PASS");
  assert.doesNotThrow(() => validateDocumentProofEvidence(passing));
  assert.throws(
    () =>
      validateDocumentProofEvidence({
        ...passing,
        results: passingResults.slice(1),
      }),
    /approved schema/,
  );
  assert.throws(
    () =>
      validateDocumentProofEvidence({
        ...passing,
        results: [passingResults[0], ...passingResults],
      }),
    /approved schema/,
  );
  assert.throws(
    () =>
      validateDocumentProofEvidence({
        ...passing,
        status: "PASS",
        results: passingResults.map((result, index) =>
          index === 0 ? { ...result, exitCode: 1 } : result,
        ),
      }),
    /passing evidence/,
  );
});

test("delivery CI retains the document proof gate and blocks image publication", async () => {
  const workflow = await read(".github/workflows/delivery.yml");

  assert.match(workflow, /document-proof-production-gate:/);
  assert.match(workflow, /run-document-proof-production-gate\.mjs/);
  assert.match(workflow, /playwright install --with-deps chromium/);
  assert.match(
    workflow,
    /document-proof-production-gate-\$\{\{ github\.run_id \}\}/,
  );
  assert.match(workflow, /retention-days: 30/);
  assert.match(
    workflow,
    /needs:[\s\S]*document-proof-production-gate,[\s\S]*runs-on:/,
  );
});

test("repository exposes one reproducible document proof gate command", async () => {
  const rootPackage = JSON.parse(await read("package.json"));

  assert.equal(
    rootPackage.scripts["gate:document-proof"],
    "node infrastructure/scripts/run-document-proof-production-gate.mjs --output document-proof-production-evidence",
  );
});
