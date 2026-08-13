import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { promisify } from "node:util";

const exec = promisify(execFile);
const scenarios = [
  {
    id: "database",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_operational_readiness.py::test_database_outage_blocks_readiness_without_leaking_connection_details",
    ],
  },
  {
    id: "redis",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_engagement.py::test_view_deduplicator_fails_closed_when_redis_is_unavailable",
    ],
  },
  {
    id: "blockchain_rpc",
    command: "python",
    arguments: [
      "-m",
      "pytest",
      "-q",
      "backend/app/tests/test_blockchain_pipeline.py::test_rpc_failure_is_durable_and_retryable",
    ],
  },
];

const plan = {
  schemaVersion: 1,
  evidenceClass: "simulation_only",
  scenarios,
};

if (process.argv[2] === "--list" && process.argv.length === 3) {
  process.stdout.write(`${JSON.stringify(plan)}\n`);
  process.exit(0);
}

if (process.argv[2] !== "--output" || process.argv.length !== 4) {
  console.error(
    "usage: run-operational-readiness-regressions.mjs --list | --output <directory>",
  );
  process.exit(64);
}

const outputDirectory = resolve(process.argv[3]);
const startedAt = new Date().toISOString();
const results = [];
const candidateRevision = process.env.GITHUB_SHA || "";
const sourceRevision = /^[a-f0-9]{40}$/i.test(candidateRevision)
  ? candidateRevision
  : "local-working-tree";

for (const scenario of scenarios) {
  const scenarioStartedAt = Date.now();
  let exitCode = 0;
  try {
    await exec(scenario.command, scenario.arguments, {
      cwd: resolve(import.meta.dirname, "../.."),
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
      maxBuffer: 1_048_576,
    });
  } catch (error) {
    exitCode = Number.isInteger(error?.code) ? error.code : 1;
  }
  results.push({
    id: scenario.id,
    exitCode,
    durationMs: Date.now() - scenarioStartedAt,
  });
}

const evidence = {
  schemaVersion: 1,
  evidenceClass: "simulation_only",
  environment: process.env.CI === "true" ? "ci" : "local",
  sourceRevision,
  startedAt,
  finishedAt: new Date().toISOString(),
  results,
  status: results.every((result) => result.exitCode === 0) ? "PASS" : "FAIL",
};
const serialized = `${JSON.stringify(evidence, null, 2)}\n`;
const digest = createHash("sha256").update(serialized).digest("hex");

await mkdir(outputDirectory, { recursive: true });
await writeFile(
  join(outputDirectory, "operational-readiness-regression.json"),
  serialized,
  { flag: "wx" },
);
await writeFile(
  join(outputDirectory, "manifest.sha256"),
  `${digest}  operational-readiness-regression.json\n`,
  { flag: "wx" },
);
process.stdout.write(
  `${JSON.stringify({ evidenceClass: evidence.evidenceClass, status: evidence.status })}\n`,
);
if (evidence.status !== "PASS") process.exit(1);
