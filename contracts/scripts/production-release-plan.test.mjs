import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

const script = resolve(import.meta.dirname, "production-release-plan.mjs");
const sourceCommit = "a".repeat(40);
const addresses = {
  deployer: `0x${"11".repeat(20)}`,
  administrator: `0x${"22".repeat(20)}`,
  issuer: `0x${"33".repeat(20)}`,
};

async function fixture() {
  const root = await mkdtemp(resolve(tmpdir(), "tmi-polygon-plan-"));
  const releaseDirectory = resolve(root, "artifacts/releases/amoy");
  await mkdir(releaseDirectory, { recursive: true });
  await writeFile(
    resolve(releaseDirectory, "manifest.json"),
    JSON.stringify({
      schemaVersion: 1,
      network: "amoy",
      chainId: 80_002,
      sourceCommit,
      compiler: { version: "0.8.30", settings: { optimizer: { runs: 200 } } },
      abiSha256: `0x${"44".repeat(32)}`,
      bytecode: {
        creationSha256: `0x${"55".repeat(32)}`,
        runtimeSha256: `0x${"66".repeat(32)}`,
      },
    }),
  );
  return root;
}

function run(root, commit = sourceCommit) {
  return spawnSync(
    process.execPath,
    [
      script,
      `--root=${root}`,
      `--source-commit=${commit}`,
      `--deployer=${addresses.deployer}`,
      `--administrator=${addresses.administrator}`,
      `--issuer=${addresses.issuer}`,
    ],
    { encoding: "utf8" },
  );
}

test("records an immutable Polygon dry-run plan from the Amoy release", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);

  const plan = JSON.parse(
    await readFile(
      resolve(root, "artifacts/releases/polygon/dry-run-plan.json"),
      "utf8",
    ),
  );
  assert.equal(plan.chainId, 137);
  assert.equal(plan.sourceCommit, sourceCommit);
  assert.equal(plan.roles.administrator, addresses.administrator);
  assert.equal(plan.roles.issuer, addresses.issuer);
  assert.equal(plan.bytecode.runtimeSha256, `0x${"66".repeat(32)}`);
  assert.match(plan.verificationCommand, /verify-contract/);
});

test("rejects a source commit different from the qualified Amoy release", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));
  const result = run(root, "b".repeat(40));
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /source commit/i);
});
