import { pathToFileURL } from "node:url";

const NETWORK_CHAIN_IDS = new Map([
  ["local", 31_337],
  ["amoy", 80_002],
  ["polygon", 137],
]);

const DEFAULT_ADMIN_ROLE_SELECTOR = "0xa217fddf";
const VERIFIER_ROLE_SELECTOR = "0xe7705db6";
const HAS_ROLE_SELECTOR = "0x91d14854";
const DEFAULT_ADMIN_ROLE = `0x${"00".repeat(32)}`;
const VERIFIER_ROLE =
  "0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09";

export const APPROVED_ADMINISTRATOR =
  "0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe".toLowerCase();
export const APPROVED_SIGNER =
  "0xBfA38182f0D24589e7898DD4892C58c3FDa58042".toLowerCase();

function requireEnvironment(environment, name) {
  const value = environment[name]?.trim();
  if (!value) {
    throw new Error(`${name} is required.`);
  }
  return value;
}

export function normalizeAddress(value) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(value)) {
    throw new Error(`Invalid Ethereum address: ${value}`);
  }
  return value.toLowerCase();
}

export function validateNetworkEnvironment(environment) {
  const network = requireEnvironment(environment, "BLOCKCHAIN_NETWORK");
  const configuredChainId = Number(
    requireEnvironment(environment, "BLOCKCHAIN_CHAIN_ID"),
  );
  const expectedChainId = NETWORK_CHAIN_IDS.get(network);
  if (
    !Number.isSafeInteger(configuredChainId) ||
    configuredChainId !== expectedChainId
  ) {
    throw new Error(
      `Invalid network/chain pair: ${network}:${configuredChainId}`,
    );
  }
  return { network, configuredChainId };
}

function parseLocalTestMode(environment) {
  const value = environment.THV_PROOF_REGISTRY_TEST_MODE?.trim();
  if (!value || value === "false") return false;
  if (value === "true") return true;
  throw new Error('THV_PROOF_REGISTRY_TEST_MODE must be "true" or "false".');
}

export function validateRoleIdentityEnvironment(environment, network) {
  const administrator = normalizeAddress(
    requireEnvironment(environment, "ADMIN_WALLET_ADDRESS"),
  );
  const signer = normalizeAddress(
    requireEnvironment(environment, "SIGNER_WALLET_ADDRESS"),
  );
  const localTestMode = parseLocalTestMode(environment);

  if (administrator === signer) {
    throw new Error(
      "ADMIN_WALLET_ADDRESS and SIGNER_WALLET_ADDRESS must be different.",
    );
  }
  if (localTestMode && network !== "local") {
    throw new Error(
      "THV_PROOF_REGISTRY_TEST_MODE is permitted only for BLOCKCHAIN_NETWORK=local.",
    );
  }
  if (!localTestMode && administrator !== APPROVED_ADMINISTRATOR) {
    throw new Error(
      "ADMIN_WALLET_ADDRESS must equal the approved THV administrator.",
    );
  }
  if (!localTestMode && signer !== APPROVED_SIGNER) {
    throw new Error(
      "SIGNER_WALLET_ADDRESS must equal the approved THV signer.",
    );
  }

  return { administrator, signer, localTestMode };
}

function validateDeployerIdentity(environment, administrator, signer) {
  const deployer = normalizeAddress(
    requireEnvironment(environment, "EXPECTED_DEPLOYER"),
  );
  if (deployer === administrator || deployer === signer) {
    throw new Error(
      "EXPECTED_DEPLOYER must be separate from Admin and Signer wallets.",
    );
  }
  return deployer;
}

export function encodeHasRole(role, account) {
  if (!/^0x[0-9a-fA-F]{64}$/.test(role)) {
    throw new Error("Role identifier must be bytes32.");
  }
  const normalizedAccount = normalizeAddress(account)
    .slice(2)
    .padStart(64, "0");
  return `${HAS_ROLE_SELECTOR}${role.slice(2).toLowerCase()}${normalizedAccount}`;
}

async function jsonRpc(fetchImpl, rpcUrl, method, params) {
  const response = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!response.ok) {
    throw new Error(`RPC ${method} failed with HTTP ${response.status}.`);
  }
  const payload = await response.json();
  if (payload.error) {
    throw new Error(
      `RPC ${method} failed: ${payload.error.message ?? "unknown error"}`,
    );
  }
  return payload.result;
}

function isTrue(hexValue) {
  if (!/^0x[0-9a-fA-F]+$/.test(hexValue)) {
    throw new Error("RPC returned invalid hexadecimal data.");
  }
  return BigInt(hexValue) === 1n;
}

export async function verifyRoles({
  environment = process.env,
  fetchImpl = globalThis.fetch,
  write = (line) => process.stdout.write(line),
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new Error(
      "A fetch implementation is required for role verification.",
    );
  }

  const { network, configuredChainId } =
    validateNetworkEnvironment(environment);
  const rpcUrl = requireEnvironment(environment, "BLOCKCHAIN_RPC_URL");
  const registry = normalizeAddress(
    requireEnvironment(environment, "THV_PROOF_REGISTRY_CONTRACT_ADDRESS"),
  );
  const { administrator, signer } = validateRoleIdentityEnvironment(
    environment,
    network,
  );
  const deployer = validateDeployerIdentity(environment, administrator, signer);

  const actualChainId = Number.parseInt(
    await jsonRpc(fetchImpl, rpcUrl, "eth_chainId", []),
    16,
  );
  if (actualChainId !== configuredChainId) {
    throw new Error(
      `RPC chain mismatch: expected ${configuredChainId}, received ${actualChainId}.`,
    );
  }

  const runtimeBytecode = await jsonRpc(fetchImpl, rpcUrl, "eth_getCode", [
    registry,
    "latest",
  ]);
  if (runtimeBytecode === "0x") {
    throw new Error(
      "No contract bytecode exists at THV_PROOF_REGISTRY_CONTRACT_ADDRESS.",
    );
  }

  const ethCall = (data) =>
    jsonRpc(fetchImpl, rpcUrl, "eth_call", [{ to: registry, data }, "latest"]);
  const defaultAdminRole = await ethCall(DEFAULT_ADMIN_ROLE_SELECTOR);
  const verifierRole = await ethCall(VERIFIER_ROLE_SELECTOR);
  if (defaultAdminRole.toLowerCase() !== DEFAULT_ADMIN_ROLE) {
    throw new Error(
      "Registry DEFAULT_ADMIN_ROLE identifier does not match AccessControl.",
    );
  }
  if (verifierRole.toLowerCase() !== VERIFIER_ROLE) {
    throw new Error(
      "Registry VERIFIER_ROLE identifier does not match THVProofRegistry.",
    );
  }
  const [
    adminHasDefaultAdmin,
    adminHasVerifier,
    signerHasVerifier,
    signerHasDefaultAdmin,
    deployerHasDefaultAdmin,
    deployerHasVerifier,
  ] = await Promise.all([
    ethCall(encodeHasRole(defaultAdminRole, administrator)),
    ethCall(encodeHasRole(verifierRole, administrator)),
    ethCall(encodeHasRole(verifierRole, signer)),
    ethCall(encodeHasRole(defaultAdminRole, signer)),
    ethCall(encodeHasRole(defaultAdminRole, deployer)),
    ethCall(encodeHasRole(verifierRole, deployer)),
  ]);

  const result = {
    chainId: actualChainId,
    registry,
    administrator,
    signer,
    deployer,
    adminHasDefaultAdmin: isTrue(adminHasDefaultAdmin),
    adminHasVerifier: isTrue(adminHasVerifier),
    signerHasVerifier: isTrue(signerHasVerifier),
    signerHasDefaultAdmin: isTrue(signerHasDefaultAdmin),
    deployerHasDefaultAdmin: isTrue(deployerHasDefaultAdmin),
    deployerHasVerifier: isTrue(deployerHasVerifier),
  };
  if (
    !result.adminHasDefaultAdmin ||
    result.adminHasVerifier ||
    !result.signerHasVerifier ||
    result.signerHasDefaultAdmin ||
    result.deployerHasDefaultAdmin ||
    result.deployerHasVerifier
  ) {
    throw new Error("Role verification failed.");
  }

  write(`THVProofRegistry roles verified on chain ${result.chainId}\n`);
  write(`admin=${result.administrator} has only DEFAULT_ADMIN_ROLE\n`);
  write(`signer=${result.signer} has only VERIFIER_ROLE\n`);
  write(`deployer=${result.deployer} retains no registry role\n`);
  return result;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  verifyRoles().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
