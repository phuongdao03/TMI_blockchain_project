import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { promisify } from "node:util";

const exec = promisify(execFile);
const repositoryRoot = resolve(import.meta.dirname, "../..");
const npmCli = join(
  dirname(process.execPath),
  "node_modules",
  "npm",
  "bin",
  "npm-cli.js",
);

export const documentProofScenarios = Object.freeze([
  {
    id: "migrations",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_private_media_encryption_migration.py",
      "backend/app/tests/test_document_hash_claim_migration.py",
      "backend/app/tests/test_document_blockchain_evidence_migration.py",
    ],
  },
  {
    id: "encryption_and_key_rotation",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_media_encryption.py",
      "backend/app/tests/test_runtime_integrations_config.py",
    ],
  },
  {
    id: "storage_and_delivery",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_media_service.py",
      "backend/app/tests/test_media_inspection_worker.py",
      "backend/app/tests/test_cloudinary_gateway.py",
    ],
  },
  {
    id: "claims_and_authorization",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_document_hash_claim_service.py",
      "backend/app/tests/test_dossier_submission.py",
      "backend/app/tests/test_authorization_matrix.py",
    ],
  },
  {
    id: "blockchain_reliability",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_document_blockchain_evidence.py",
      "backend/app/tests/test_document_blockchain_evidence_pipeline.py",
      "backend/app/tests/test_blockchain_pipeline.py",
      "backend/app/tests/test_certificate_version_blockchain.py",
    ],
  },
  {
    id: "verification_and_leakage",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_document_verification.py",
      "backend/app/tests/test_document_verification_api.py",
      "backend/app/tests/test_review_media_access.py",
      "backend/app/tests/test_public_catalog_security_gate.py",
    ],
  },
  {
    id: "frontend_verification",
    command: process.platform === "win32" ? process.execPath : "npm",
    arguments: [
      ...(process.platform === "win32" ? [npmCli] : []),
      "--prefix",
      "frontend",
      "run",
      "test",
      "--",
      "--run",
      "src/components/public/verification-panel.test.tsx",
      "src/components/documents/private-document-verification.test.tsx",
      "src/lib/api/client.test.ts",
    ],
  },
  {
    id: "verification_e2e",
    command: process.platform === "win32" ? process.execPath : "npm",
    arguments: [
      ...(process.platform === "win32" ? [npmCli] : []),
      "--prefix",
      "frontend",
      "run",
      "test:e2e",
      "--",
      "public-verification.spec.ts",
    ],
  },
  {
    id: "contract_document_evidence",
    command: "docker",
    arguments: [
      "run",
      "--rm",
      "--user",
      "root",
      "--entrypoint",
      "forge",
      "-v",
      `${resolve(repositoryRoot, "contracts")}:/workspace`,
      "-w",
      "/workspace",
      "ghcr.io/foundry-rs/foundry:v1.7.1",
      "test",
      "--match-contract",
      "CertificateRegistryTest",
      "--fuzz-runs",
      "256",
    ],
  },
  {
    id: "anvil_document_evidence",
    command:
      process.platform === "win32"
        ? "C:\\Program Files\\Git\\bin\\bash.exe"
        : "bash",
    arguments: ["contracts/scripts/smoke-anvil.sh"],
  },
]);

const evidenceKeys = [
  "schemaVersion",
  "evidenceClass",
  "releaseScope",
  "environment",
  "sourceRevision",
  "startedAt",
  "finishedAt",
  "results",
  "status",
];
const resultKeys = ["id", "exitCode", "durationMs"];
const exactKeys = (value, expected) =>
  value !== null &&
  typeof value === "object" &&
  !Array.isArray(value) &&
  JSON.stringify(Object.keys(value).sort()) ===
    JSON.stringify([...expected].sort());
const isTimestamp = (value) =>
  typeof value === "string" && Number.isFinite(Date.parse(value));
const approvedScenarioIds = documentProofScenarios.map(({ id }) => id);

export function createDocumentProofEvidence({
  environment,
  sourceRevision,
  startedAt,
  finishedAt,
  results,
}) {
  return {
    schemaVersion: 1,
    evidenceClass: "automated_document_proof_qualification",
    releaseScope: "document_proof_only",
    environment,
    sourceRevision,
    startedAt,
    finishedAt,
    results,
    status: results.every(({ exitCode }) => exitCode === 0) ? "PASS" : "FAIL",
  };
}

export function validateDocumentProofEvidence(evidence) {
  const validRevision =
    evidence?.sourceRevision === "local-working-tree" ||
    /^[a-f0-9]{40}$/i.test(evidence?.sourceRevision ?? "");
  const resultIds = Array.isArray(evidence?.results)
    ? evidence.results.map(({ id }) => id)
    : [];
  const resultsMatch =
    JSON.stringify(resultIds) === JSON.stringify(approvedScenarioIds);
  const validResults =
    resultsMatch &&
    evidence.results.every(
      (result) =>
        exactKeys(result, resultKeys) &&
        Number.isInteger(result.exitCode) &&
        result.exitCode >= 0 &&
        Number.isInteger(result.durationMs) &&
        result.durationMs >= 0,
    );

  if (
    !exactKeys(evidence, evidenceKeys) ||
    evidence.schemaVersion !== 1 ||
    evidence.evidenceClass !== "automated_document_proof_qualification" ||
    evidence.releaseScope !== "document_proof_only" ||
    !["ci", "local"].includes(evidence.environment) ||
    !validRevision ||
    !isTimestamp(evidence.startedAt) ||
    !isTimestamp(evidence.finishedAt) ||
    Date.parse(evidence.finishedAt) < Date.parse(evidence.startedAt) ||
    !validResults ||
    !["PASS", "FAIL"].includes(evidence.status)
  ) {
    throw new Error(
      "document proof evidence does not match the approved schema",
    );
  }
  const allPassed = evidence.results.every(({ exitCode }) => exitCode === 0);
  if (evidence.status === "PASS" && !allPassed) {
    throw new Error("passing evidence contains a failed scenario");
  }
  if (evidence.status === "FAIL" && allPassed) {
    throw new Error("failed evidence contains no failed scenario");
  }
  return evidence;
}

async function runScenario(scenario, temporaryRoot) {
  const startedAt = Date.now();
  let exitCode = 0;
  const scenarioArguments =
    scenario.command === "python"
      ? [
          ...scenario.arguments,
          "--basetemp",
          join(temporaryRoot, scenario.id),
          "-p",
          "no:cacheprovider",
        ]
      : scenario.arguments;
  try {
    await exec(scenario.command, scenarioArguments, {
      cwd: repositoryRoot,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
      maxBuffer: 1_048_576,
    });
  } catch (error) {
    exitCode = Number.isInteger(error?.code) ? error.code : 1;
    const output = [error?.stdout, error?.stderr]
      .filter((value) => typeof value === "string" && value.trim())
      .join("\n")
      .trim();
    if (output) {
      const boundedOutput = output.slice(-8_192);
      process.stderr.write(
        `[document-proof:${scenario.id}] failed\n${boundedOutput}\n`,
      );
    }
  }
  return {
    id: scenario.id,
    exitCode,
    durationMs: Date.now() - startedAt,
  };
}

async function main() {
  if (process.argv[2] === "--list" && process.argv.length === 3) {
    process.stdout.write(
      `${JSON.stringify({
        schemaVersion: 1,
        evidenceClass: "automated_document_proof_qualification",
        releaseScope: "document_proof_only",
        scenarios: documentProofScenarios,
      })}\n`,
    );
    return;
  }
  if (process.argv[2] !== "--output" || process.argv.length !== 4) {
    console.error(
      "usage: run-document-proof-production-gate.mjs --list | --output <directory>",
    );
    process.exitCode = 64;
    return;
  }

  const outputDirectory = resolve(process.argv[3]);
  const startedAt = new Date().toISOString();
  const results = [];
  const temporaryRoot = await mkdtemp(
    join(repositoryRoot, ".document-proof-gate-"),
  );
  try {
    for (const scenario of documentProofScenarios) {
      results.push(await runScenario(scenario, temporaryRoot));
    }
  } finally {
    await rm(temporaryRoot, { recursive: true, force: true });
  }
  const candidateRevision = process.env.GITHUB_SHA ?? "";
  const evidence = createDocumentProofEvidence({
    environment: process.env.CI === "true" ? "ci" : "local",
    sourceRevision: /^[a-f0-9]{40}$/i.test(candidateRevision)
      ? candidateRevision
      : "local-working-tree",
    startedAt,
    finishedAt: new Date().toISOString(),
    results,
  });
  validateDocumentProofEvidence(evidence);

  const serialized = `${JSON.stringify(evidence, null, 2)}\n`;
  const digest = createHash("sha256").update(serialized).digest("hex");
  await mkdir(outputDirectory, { recursive: true });
  await writeFile(
    join(outputDirectory, "document-proof-production-gate.json"),
    serialized,
    { flag: "wx" },
  );
  await writeFile(
    join(outputDirectory, "manifest.sha256"),
    `${digest}  document-proof-production-gate.json\n`,
    { flag: "wx" },
  );
  process.stdout.write(
    `${JSON.stringify({ releaseScope: evidence.releaseScope, status: evidence.status })}\n`,
  );
  if (evidence.status !== "PASS") process.exitCode = 1;
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) {
  await main();
}
