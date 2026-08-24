import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

const script = resolve(import.meta.dirname, "export-thv-proof-registry-artifacts.mjs");
const sourceCommit = "a".repeat(40);
const contractAddress = `0x${"12".repeat(20)}`;
const transactionHash = `0x${"34".repeat(32)}`;
const administrator = "0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe";
const signer = "0xBfA38182f0D24589e7898DD4892C58c3FDa58042";

async function fixture() {
  const root = await mkdtemp(resolve(tmpdir(), "thv-export-release-"));
  const artifactDirectory = resolve(root, "out", "THVProofRegistry.sol");
  const broadcastDirectory = resolve(
    root,
    "broadcast",
    "DeployTHVProofRegistry.s.sol",
    "137",
  );
  const planDirectory = resolve(root, "artifacts", "releases", "polygon");
  await Promise.all([
    mkdir(artifactDirectory, { recursive: true }),
    mkdir(broadcastDirectory, { recursive: true }),
    mkdir(planDirectory, { recursive: true }),
  ]);
  await writeFile(
    resolve(artifactDirectory, "THVProofRegistry.json"),
    JSON.stringify({
      abi: [{ type: "function", name: "recordProof", inputs: [] }],
      bytecode: { object: `0x${"11".repeat(12)}` },
      deployedBytecode: { object: `0x${"22".repeat(10)}` },
      metadata: {
        compiler: { version: "0.8.30+commit.73712a01" },
        settings: { optimizer: { enabled: true, runs: 200 } },
      },
    }),
  );
  await writeFile(
    resolve(broadcastDirectory, "run-latest.json"),
    JSON.stringify({
      chain: 137,
      transactions: [
        {
          transactionType: "CREATE",
          contractName: "THVProofRegistry",
          contractAddress,
          hash: transactionHash,
        },
      ],
    }),
  );
  await writeFile(
    resolve(planDirectory, "thv-proof-registry-deployment-plan.json"),
    JSON.stringify({
      contract: "THVProofRegistry",
      network: "polygon",
      chainId: 137,
      sourceCommit,
      roles: { defaultAdmin: administrator, verifier: signer },
    }),
  );
  return root;
}

function run(root, overrides = {}) {
  const options = {
    root,
    network: "polygon",
    "chain-id": "137",
    "source-commit": sourceCommit,
    ...overrides,
  };
  return spawnSync(
    process.execPath,
    [script, ...Object.entries(options).map(([key, value]) => `--${key}=${value}`)],
    { encoding: "utf8" },
  );
}

test("exports a reproducible THVProofRegistry Mainnet manifest from broadcast evidence", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  const manifest = JSON.parse(
    await readFile(
      resolve(root, "artifacts", "releases", "polygon", "thv-proof-registry-manifest.json"),
      "utf8",
    ),
  );
  assert.equal(manifest.contract, "THVProofRegistry");
  assert.equal(manifest.proofRegistry, contractAddress);
  assert.equal(manifest.deploymentTransactionHash, transactionHash);
  assert.equal(manifest.roles.defaultAdmin, administrator);
  assert.equal(manifest.roles.verifier, signer);
  assert.match(manifest.bytecode.runtimeSha256, /^0x[0-9a-f]{64}$/);
});

test("rejects broadcast evidence for a different chain", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root, { "chain-id": "80002" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /restricted to polygon:137/i);
});

test("rejects a source commit that differs from the reviewed deployment plan", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root, { "source-commit": "b".repeat(40) });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /does not match/i);
});
