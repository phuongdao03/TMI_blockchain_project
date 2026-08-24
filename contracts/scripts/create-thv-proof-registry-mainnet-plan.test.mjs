import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { test } from "node:test";

const script = resolve(
  import.meta.dirname,
  "create-thv-proof-registry-mainnet-plan.mjs",
);
const administrator = "0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe";
const signer = "0xBfA38182f0D24589e7898DD4892C58c3FDa58042";
const deployer = `0x${"12".repeat(20)}`;

async function fixture() {
  const root = await mkdtemp(resolve(tmpdir(), "thv-mainnet-plan-"));
  const artifactDirectory = resolve(root, "out", "THVProofRegistry.sol");
  await mkdir(artifactDirectory, { recursive: true });
  await writeFile(
    resolve(artifactDirectory, "THVProofRegistry.json"),
    JSON.stringify({
      abi: [{ type: "constructor", inputs: [] }],
      bytecode: { object: `0x${"11".repeat(12)}` },
      deployedBytecode: { object: `0x${"22".repeat(10)}` },
      metadata: {
        compiler: { version: "0.8.30+commit.73712a01" },
        settings: { optimizer: { enabled: true, runs: 200 } },
      },
    }),
  );
  for (const path of [
    "foundry.toml",
    "package.json",
    "package-lock.json",
    "src/THVProofRegistry.sol",
    "script/DeployTHVProofRegistry.s.sol",
    "test/THVProofRegistry.t.sol",
    "test/DeployTHVProofRegistry.t.sol",
    "scripts/deploy-thv-proof-registry.sh",
    "scripts/read-thv-proof-registry-mainnet-broadcast-evidence.mjs",
    "scripts/verify-thv-proof-registry-roles.mjs",
    "scripts/create-thv-proof-registry-mainnet-plan.mjs",
    "scripts/preflight-thv-proof-registry-mainnet.mjs",
    "scripts/export-thv-proof-registry-artifacts.mjs",
    "artifacts/THVProofRegistry.abi.json",
  ]) {
    const file = resolve(root, path);
    await mkdir(resolve(file, ".."), { recursive: true });
    await writeFile(file, "release input\n");
  }
  execFileSync("git", ["init"], { cwd: root, stdio: "ignore" });
  execFileSync("git", ["config", "user.email", "thv-tests@example.invalid"], {
    cwd: root,
  });
  execFileSync("git", ["config", "user.name", "THV Tests"], { cwd: root });
  execFileSync("git", ["add", "."], { cwd: root });
  execFileSync("git", ["commit", "-m", "release fixture"], {
    cwd: root,
    stdio: "ignore",
  });
  return {
    root,
    sourceCommit: execFileSync("git", ["rev-parse", "HEAD"], {
      cwd: root,
      encoding: "utf8",
    }).trim(),
  };
}

function run(root, sourceCommit, overrides = {}) {
  const options = {
    root,
    "source-commit": sourceCommit,
    deployer,
    administrator,
    signer,
    ...overrides,
  };
  return spawnSync(
    process.execPath,
    [
      script,
      ...Object.entries(options).map(([key, value]) => `--${key}=${value}`),
    ],
    { encoding: "utf8" },
  );
}

test("creates an immutable direct-Polygon deployment plan for approved identities", async (context) => {
  const { root, sourceCommit } = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root, sourceCommit);
  assert.equal(result.status, 0, result.stderr);

  const plan = JSON.parse(
    await readFile(
      resolve(
        root,
        "artifacts",
        "releases",
        "polygon",
        "thv-proof-registry-deployment-plan.json",
      ),
      "utf8",
    ),
  );
  assert.equal(plan.network, "polygon");
  assert.equal(plan.chainId, 137);
  assert.equal(plan.sourceCommit, sourceCommit);
  assert.equal(plan.roles.defaultAdmin, administrator);
  assert.equal(plan.roles.verifier, signer);
  assert.equal(plan.roles.deployer, deployer.toLowerCase());
  assert.match(plan.deploymentCommand, /--confirm-mainnet/);
  assert.match(plan.verificationCommand, /verify-contract/);
  assert.match(plan.bytecode.runtimeSha256, /^0x[0-9a-f]{64}$/);
});

test("rejects a role address that differs from the approved administrator", async (context) => {
  const { root, sourceCommit } = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root, sourceCommit, {
    administrator: `0x${"34".repeat(20)}`,
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /approved Admin/i);
});

test("rejects a deployer wallet that overlaps a governance role", async (context) => {
  const { root, sourceCommit } = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = run(root, sourceCommit, { deployer: administrator });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /separate from Admin and Signer/i);
});

test("rejects release inputs that are not committed at the selected source commit", async (context) => {
  const { root, sourceCommit } = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));
  await writeFile(
    resolve(root, "src", "THVProofRegistry.sol"),
    "changed after release\n",
  );

  const result = run(root, sourceCommit);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /uncommitted changes/i);
});
