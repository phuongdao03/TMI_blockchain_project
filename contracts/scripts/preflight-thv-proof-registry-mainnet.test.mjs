import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";

import { runPreflight } from "./preflight-thv-proof-registry-mainnet.mjs";

const ADMIN = "0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe";
const SIGNER = "0xBfA38182f0D24589e7898DD4892C58c3FDa58042";
const DEPLOYER = `0x${"12".repeat(20)}`;
const SOURCE_COMMIT = "a".repeat(40);

async function fixture() {
  const root = await mkdtemp(resolve(tmpdir(), "thv-mainnet-preflight-"));
  const artifactDirectory = resolve(root, "out", "THVProofRegistry.sol");
  const releaseDirectory = resolve(root, "artifacts", "releases", "polygon");
  await Promise.all([
    mkdir(artifactDirectory, { recursive: true }),
    mkdir(releaseDirectory, { recursive: true }),
  ]);
  await writeFile(
    resolve(artifactDirectory, "THVProofRegistry.json"),
    JSON.stringify({
      bytecode: { object: `0x${"11".repeat(12)}` },
    }),
  );
  await writeFile(
    resolve(releaseDirectory, "thv-proof-registry-deployment-plan.json"),
    JSON.stringify({
      contract: "THVProofRegistry",
      network: "polygon",
      chainId: 137,
      sourceCommit: SOURCE_COMMIT,
      roles: {
        deployer: DEPLOYER.toLowerCase(),
        defaultAdmin: ADMIN,
        verifier: SIGNER,
        deploymentKeyRetainsRole: false,
      },
    }),
  );
  return root;
}

function environment(overrides = {}) {
  return {
    BLOCKCHAIN_NETWORK: "polygon",
    BLOCKCHAIN_CHAIN_ID: "137",
    BLOCKCHAIN_RPC_URL: "https://polygon-rpc.example",
    ADMIN_WALLET_ADDRESS: ADMIN,
    SIGNER_WALLET_ADDRESS: SIGNER,
    EXPECTED_DEPLOYER: DEPLOYER,
    SOURCE_COMMIT,
    MINIMUM_DEPLOYER_BALANCE_WEI: "1000",
    ...overrides,
  };
}

function rpc({ chainId = "0x89", balance = "0x1000000000000000" } = {}) {
  return async (_url, request) => {
    const { method } = JSON.parse(request.body);
    const result = {
      eth_chainId: chainId,
      eth_getBalance: balance,
      eth_estimateGas: "0x5208",
      eth_gasPrice: "0x3b9aca00",
    }[method];
    return { ok: true, status: 200, json: async () => ({ result }) };
  };
}

test("passes only after Mainnet, immutable plan, role identities and balance are verified", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  const result = await runPreflight({
    root,
    environment: environment(),
    fetchImpl: rpc(),
    write: () => {},
  });

  assert.equal(result.chainId, 137);
  assert.equal(result.deployer, DEPLOYER.toLowerCase());
  assert.equal(result.gasEstimate, 21_000n);
  assert.equal(result.requiredBalanceWei > result.estimatedCostWei, true);
});

test("rejects a non-Mainnet RPC before any deployment command can run", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  await assert.rejects(
    () =>
      runPreflight({
        root,
        environment: environment(),
        fetchImpl: rpc({ chainId: "0x13882" }),
        write: () => {},
      }),
    /RPC chain mismatch/i,
  );
});

test("rejects a deployer balance below the dynamically estimated safety floor", async (context) => {
  const root = await fixture();
  context.after(() => rm(root, { recursive: true, force: true }));

  await assert.rejects(
    () =>
      runPreflight({
        root,
        environment: environment({ MINIMUM_DEPLOYER_BALANCE_WEI: "0" }),
        fetchImpl: rpc({ balance: "0x1" }),
        write: () => {},
      }),
    /balance is below/i,
  );
});
