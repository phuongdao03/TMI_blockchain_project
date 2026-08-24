import assert from "node:assert/strict";
import test from "node:test";

import {
  APPROVED_ADMINISTRATOR,
  APPROVED_SIGNER,
  verifyRoles,
} from "./verify-thv-proof-registry-roles.mjs";

const REGISTRY = "0x1111111111111111111111111111111111111111";
const ADMIN = APPROVED_ADMINISTRATOR;
const SIGNER = APPROVED_SIGNER;
const DEPLOYER = "0x4444444444444444444444444444444444444444";
const LOCAL_TEST_ADMIN = "0x2222222222222222222222222222222222222222";
const LOCAL_TEST_SIGNER = "0x3333333333333333333333333333333333333333";
const DEFAULT_ADMIN_ROLE = `0x${"00".repeat(32)}`;
const VERIFIER_ROLE =
  "0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09";

function roleFetch({
  chainId = "0x7a69",
  administrator = ADMIN,
  signer = SIGNER,
  deployer = DEPLOYER,
  defaultAdminRole = DEFAULT_ADMIN_ROLE,
  verifierRole = VERIFIER_ROLE,
  administratorHasVerifier = false,
  signerHasVerifier = true,
  deployerHasVerifier = false,
} = {}) {
  return async (_url, request) => {
    const { method, params } = JSON.parse(request.body);
    let result;
    if (method === "eth_chainId") result = chainId;
    if (method === "eth_getCode") result = "0x6000";
    if (method === "eth_call") {
      const data = params[0].data.toLowerCase();
      if (data === "0xa217fddf") result = defaultAdminRole;
      if (data === "0xe7705db6") result = verifierRole;
      if (data.startsWith("0x91d14854")) {
        const role = `0x${data.slice(10, 74)}`;
        const account = `0x${data.slice(-40)}`;
        result = DEFAULT_ADMIN_ROLE;
        if (
          account === administrator.toLowerCase() &&
          role === DEFAULT_ADMIN_ROLE
        ) {
          result = `0x${"00".repeat(31)}01`;
        }
        if (
          account === administrator.toLowerCase() &&
          role === VERIFIER_ROLE &&
          administratorHasVerifier
        ) {
          result = `0x${"00".repeat(31)}01`;
        }
        if (
          account === signer.toLowerCase() &&
          role === VERIFIER_ROLE &&
          signerHasVerifier
        ) {
          result = `0x${"00".repeat(31)}01`;
        }
        if (
          account === deployer.toLowerCase() &&
          role === VERIFIER_ROLE &&
          deployerHasVerifier
        ) {
          result = `0x${"00".repeat(31)}01`;
        }
      }
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ jsonrpc: "2.0", id: 1, result }),
    };
  };
}

function environment() {
  return {
    BLOCKCHAIN_NETWORK: "local",
    BLOCKCHAIN_CHAIN_ID: "31337",
    BLOCKCHAIN_RPC_URL: "http://127.0.0.1:8545",
    THV_PROOF_REGISTRY_CONTRACT_ADDRESS: REGISTRY,
    ADMIN_WALLET_ADDRESS: ADMIN,
    SIGNER_WALLET_ADDRESS: SIGNER,
    EXPECTED_DEPLOYER: DEPLOYER,
  };
}

test("verifies expected initial role separation", async () => {
  const result = await verifyRoles({
    environment: environment(),
    fetchImpl: roleFetch(),
    write: () => {},
  });
  assert.equal(result.adminHasDefaultAdmin, true);
  assert.equal(result.adminHasVerifier, false);
  assert.equal(result.signerHasVerifier, true);
  assert.equal(result.signerHasDefaultAdmin, false);
  assert.equal(result.deployerHasDefaultAdmin, false);
  assert.equal(result.deployerHasVerifier, false);
});

test("rejects a mismatched RPC chain", async () => {
  await assert.rejects(
    () =>
      verifyRoles({
        environment: environment(),
        fetchImpl: roleFetch({ chainId: "0x89" }),
        write: () => {},
      }),
    /RPC chain mismatch/,
  );
});

test("rejects an unexpected verifier assignment", async () => {
  await assert.rejects(
    () =>
      verifyRoles({
        environment: environment(),
        fetchImpl: roleFetch({ signerHasVerifier: false }),
        write: () => {},
      }),
    /Role verification failed/,
  );
});

test("rejects unexpected role identifiers", async () => {
  await assert.rejects(
    () =>
      verifyRoles({
        environment: environment(),
        fetchImpl: roleFetch({ verifierRole: DEFAULT_ADMIN_ROLE }),
        write: () => {},
      }),
    /VERIFIER_ROLE identifier/,
  );
});

test("rejects deployment accounts that retain a registry role", async () => {
  await assert.rejects(
    () =>
      verifyRoles({
        environment: environment(),
        fetchImpl: roleFetch({ deployerHasVerifier: true }),
        write: () => {},
      }),
    /Role verification failed/,
  );
});

test("rejects a non-approved administrator outside explicit local test mode", async () => {
  const invalidEnvironment = {
    ...environment(),
    ADMIN_WALLET_ADDRESS: LOCAL_TEST_ADMIN,
  };

  await assert.rejects(
    () =>
      verifyRoles({
        environment: invalidEnvironment,
        fetchImpl: roleFetch(),
        write: () => {},
      }),
    /ADMIN_WALLET_ADDRESS must equal the approved THV administrator/,
  );
});

test("rejects a non-approved signer outside explicit local test mode", async () => {
  const invalidEnvironment = {
    ...environment(),
    SIGNER_WALLET_ADDRESS: LOCAL_TEST_SIGNER,
  };

  await assert.rejects(
    () =>
      verifyRoles({
        environment: invalidEnvironment,
        fetchImpl: roleFetch(),
        write: () => {},
      }),
    /SIGNER_WALLET_ADDRESS must equal the approved THV signer/,
  );
});

test("permits non-production identities only in explicit local test mode", async () => {
  const localTestEnvironment = {
    ...environment(),
    ADMIN_WALLET_ADDRESS: LOCAL_TEST_ADMIN,
    SIGNER_WALLET_ADDRESS: LOCAL_TEST_SIGNER,
    THV_PROOF_REGISTRY_TEST_MODE: "true",
  };

  const result = await verifyRoles({
    environment: localTestEnvironment,
    fetchImpl: roleFetch({
      administrator: LOCAL_TEST_ADMIN,
      signer: LOCAL_TEST_SIGNER,
    }),
    write: () => {},
  });

  assert.equal(result.administrator, LOCAL_TEST_ADMIN);
  assert.equal(result.signer, LOCAL_TEST_SIGNER);
});

test("rejects test mode on Polygon Mainnet", async () => {
  const invalidEnvironment = {
    ...environment(),
    BLOCKCHAIN_NETWORK: "polygon",
    BLOCKCHAIN_CHAIN_ID: "137",
    THV_PROOF_REGISTRY_TEST_MODE: "true",
  };

  await assert.rejects(
    () =>
      verifyRoles({
        environment: invalidEnvironment,
        fetchImpl: roleFetch({ chainId: "0x89" }),
        write: () => {},
      }),
    /THV_PROOF_REGISTRY_TEST_MODE is permitted only for BLOCKCHAIN_NETWORK=local/,
  );
});

test("rejects malformed local test mode values", async () => {
  const invalidEnvironment = {
    ...environment(),
    THV_PROOF_REGISTRY_TEST_MODE: "1",
  };

  await assert.rejects(
    () =>
      verifyRoles({
        environment: invalidEnvironment,
        fetchImpl: roleFetch(),
        write: () => {},
      }),
    /THV_PROOF_REGISTRY_TEST_MODE must be "true" or "false"/,
  );
});

test("rejects overlapping administrator and signer identities", async () => {
  const invalidEnvironment = {
    ...environment(),
    SIGNER_WALLET_ADDRESS: ADMIN,
  };

  await assert.rejects(
    () =>
      verifyRoles({
        environment: invalidEnvironment,
        fetchImpl: roleFetch(),
        write: () => {},
      }),
    /ADMIN_WALLET_ADDRESS and SIGNER_WALLET_ADDRESS must be different/,
  );
});
