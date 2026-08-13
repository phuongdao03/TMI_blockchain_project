import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

const script = resolve(import.meta.dirname, "record-explorer-evidence.mjs");
const address = `0x${"12".repeat(20)}`;
const sourceCommit = "a".repeat(40);

async function fixture() {
  const root = await mkdtemp(resolve(tmpdir(), "tmi-explorer-evidence-"));
  const releaseDirectory = resolve(root, "artifacts/releases/amoy");
  await mkdir(releaseDirectory, { recursive: true });
  await writeFile(
    resolve(releaseDirectory, "manifest.json"),
    JSON.stringify({
      network: "amoy",
      chainId: 80_002,
      sourceCommit,
      certificateRegistry: address,
      deploymentTransactionHash: `0x${"34".repeat(32)}`,
    }),
  );
  return root;
}

function run(root, overrideAddress = address) {
  return spawnSync(
    process.execPath,
    [
      script,
      "--network=amoy",
      "--chain-id=80002",
      `--address=${overrideAddress}`,
      "--explorer-base-url=https://amoy.polygonscan.com",
      `--source-commit=${sourceCommit}`,
      `--root=${root}`,
    ],
    { encoding: "utf8" },
  );
}

test("records evidence only after it matches the release manifest", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  const evidence = JSON.parse(
    await readFile(
      resolve(root, "artifacts/releases/amoy/explorer-evidence.json"),
      "utf8",
    ),
  );
  assert.equal(evidence.verificationStatus, "verified");
  assert.equal(evidence.certificateRegistry, address);
  assert.equal(
    evidence.contractUrl,
    `https://amoy.polygonscan.com/address/${address}#code`,
  );
});

test("rejects evidence for a different deployed address", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root, `0x${"56".repeat(20)}`);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /does not match/i);
});
