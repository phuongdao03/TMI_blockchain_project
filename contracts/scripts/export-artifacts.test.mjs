import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { test } from "node:test";
import { spawnSync } from "node:child_process";

const script = resolve(import.meta.dirname, "export-artifacts.mjs");
const sourceCommit = "a".repeat(40);

function sha256Hex(value) {
  return `0x${createHash("sha256")
    .update(Buffer.from(value.replace(/^0x/, ""), "hex"))
    .digest("hex")}`;
}

async function fixture() {
  const root = await mkdtemp(resolve(tmpdir(), "tmi-contract-release-"));
  const artifactDirectory = resolve(root, "out/CertificateRegistry.sol");
  const broadcastDirectory = resolve(
    root,
    "broadcast/DeployCertificateRegistry.s.sol/31337",
  );
  await mkdir(artifactDirectory, { recursive: true });
  await mkdir(broadcastDirectory, { recursive: true });
  await writeFile(
    resolve(artifactDirectory, "CertificateRegistry.json"),
    JSON.stringify({
      abi: [{ type: "function", name: "getCertificate", inputs: [] }],
      bytecode: { object: "0x60016002" },
      deployedBytecode: { object: "0x6002" },
      metadata: JSON.stringify({
        compiler: { version: "0.8.30+commit.73712a01" },
        settings: {
          optimizer: { enabled: true, runs: 200 },
          metadata: { bytecodeHash: "none" },
        },
      }),
    }),
  );
  await writeFile(
    resolve(broadcastDirectory, "run-latest.json"),
    JSON.stringify({
      chain: 31337,
      transactions: [
        {
          transactionType: "CREATE",
          contractName: "CertificateRegistry",
          contractAddress: `0x${"12".repeat(20)}`,
          hash: `0x${"34".repeat(32)}`,
        },
      ],
    }),
  );
  return root;
}

test("exports deterministic contract provenance", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));
  const result = spawnSync(
    process.execPath,
    [
      script,
      "--network=local",
      "--chain-id=31337",
      `--root=${root}`,
      `--source-commit=${sourceCommit}`,
    ],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 0, result.stderr);

  const manifestPath = resolve(root, "artifacts/releases/local/manifest.json");
  const first = await readFile(manifestPath, "utf8");
  const manifest = JSON.parse(first);
  assert.equal(manifest.schemaVersion, 1);
  assert.equal(manifest.sourceCommit, sourceCommit);
  assert.deepEqual(manifest.compiler, {
    version: "0.8.30+commit.73712a01",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      metadata: { bytecodeHash: "none" },
    },
  });
  assert.equal(manifest.bytecode.creationSha256, sha256Hex("0x60016002"));
  assert.equal(manifest.bytecode.runtimeSha256, sha256Hex("0x6002"));
  assert.match(manifest.abiSha256, /^0x[0-9a-f]{64}$/);

  const rerun = spawnSync(
    process.execPath,
    [
      script,
      "--network=local",
      "--chain-id=31337",
      `--root=${root}`,
      `--source-commit=${sourceCommit}`,
    ],
    { encoding: "utf8" },
  );
  assert.equal(rerun.status, 0, rerun.stderr);
  assert.equal(await readFile(manifestPath, "utf8"), first);
});

test("rejects a source commit that cannot identify the release", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));
  const result = spawnSync(
    process.execPath,
    [
      script,
      "--network=local",
      "--chain-id=31337",
      `--root=${root}`,
      "--source-commit=not-a-commit",
    ],
    { encoding: "utf8" },
  );
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /source commit/i);
});

test("accepts Foundry's source-qualified contract name", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));
  const broadcastPath = resolve(
    root,
    "broadcast/DeployCertificateRegistry.s.sol/31337/run-latest.json",
  );
  const broadcast = JSON.parse(await readFile(broadcastPath, "utf8"));
  broadcast.transactions[0].contractName =
    "CertificateRegistry.sol/CertificateRegistry";
  await writeFile(broadcastPath, JSON.stringify(broadcast));

  const result = spawnSync(
    process.execPath,
    [
      script,
      "--network=local",
      "--chain-id=31337",
      `--root=${root}`,
      `--source-commit=${sourceCommit}`,
    ],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 0, result.stderr);
});
