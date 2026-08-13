import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { generateKeyPairSync } from "node:crypto";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import test from "node:test";

const exec = promisify(execFile);
const root = new URL("../", import.meta.url);
const script = (name) =>
  fileURLToPath(new URL(`infrastructure/scripts/${name}`, root));

test("restore runbook requires independent signature verification", async () => {
  const runbook = await readFile(
    new URL("docs/runbooks/backup-and-restore.md", root),
    "utf8",
  );
  assert.match(runbook, /sign-readiness-evidence\.mjs/);
  assert.match(runbook, /verify-readiness-evidence\.mjs/);
  assert.match(runbook, /READINESS_EVIDENCE_PRIVATE_KEY_FILE/);
  assert.match(runbook, /READINESS_EVIDENCE_PUBLIC_KEY_FILE/);
  assert.match(runbook, /independent verifier/i);
});

test("recovery evidence is validated, signed and tamper evident", async () => {
  const directory = await mkdtemp(join(tmpdir(), "tmi-readiness-"));
  const evidencePath = join(directory, "restore-evidence.json");
  const signaturePath = join(directory, "restore-evidence.sig");
  const privateKeyPath = join(directory, "private.pem");
  const publicKeyPath = join(directory, "public.pem");
  const { privateKey, publicKey } = generateKeyPairSync("ed25519");
  await writeFile(
    privateKeyPath,
    privateKey.export({ type: "pkcs8", format: "pem" }),
    { mode: 0o600 },
  );
  await writeFile(
    publicKeyPath,
    publicKey.export({ type: "spki", format: "pem" }),
  );
  const evidence = {
    schemaVersion: 1,
    drillType: "postgres_restore",
    environment: "staging",
    startedAt: "2026-08-11T08:00:00Z",
    finishedAt: "2026-08-11T09:20:00Z",
    targets: { rpoMinutes: 1440, rtoMinutes: 240 },
    achieved: { rpoMinutes: 30, rtoMinutes: 80 },
    source: {
      backupId: "staging-backup-20260811",
      manifestSha256: "a".repeat(64),
      migrationRevision: "0050_job_operations_permission",
      imageTag: "sha-0123456789abcdef",
    },
    checks: {
      checksumVerified: true,
      smokeTestsPassed: true,
      duplicateSideEffectsDetected: false,
    },
    approvals: {
      owner: "platform-owner",
      independentVerifier: "security-reviewer",
    },
    status: "PASS",
  };
  await writeFile(evidencePath, JSON.stringify(evidence));

  await exec(
    process.execPath,
    [script("sign-readiness-evidence.mjs"), evidencePath, signaturePath],
    {
      env: {
        ...process.env,
        READINESS_EVIDENCE_PRIVATE_KEY_FILE: privateKeyPath,
      },
    },
  );
  const verified = await exec(
    process.execPath,
    [script("verify-readiness-evidence.mjs"), evidencePath, signaturePath],
    {
      env: {
        ...process.env,
        READINESS_EVIDENCE_PUBLIC_KEY_FILE: publicKeyPath,
      },
    },
  );
  assert.match(verified.stdout, /"verified":true/);

  await writeFile(evidencePath, `${await readFile(evidencePath, "utf8")} `);
  await assert.rejects(
    exec(
      process.execPath,
      [script("verify-readiness-evidence.mjs"), evidencePath, signaturePath],
      {
        env: {
          ...process.env,
          READINESS_EVIDENCE_PUBLIC_KEY_FILE: publicKeyPath,
        },
      },
    ),
  );

  evidence.achieved.rtoMinutes = 241;
  await writeFile(evidencePath, JSON.stringify(evidence));
  await assert.rejects(
    exec(
      process.execPath,
      [script("sign-readiness-evidence.mjs"), evidencePath, signaturePath],
      {
        env: {
          ...process.env,
          READINESS_EVIDENCE_PRIVATE_KEY_FILE: privateKeyPath,
        },
      },
    ),
  );
});
