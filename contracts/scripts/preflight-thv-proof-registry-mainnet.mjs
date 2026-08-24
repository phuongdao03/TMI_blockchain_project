import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const contractRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const APPROVED_ADMIN =
  "0xec5fcdFab3FCafCEFCED55CC702CD3B13f54B4Fe".toLowerCase();
const APPROVED_SIGNER = "0xbfa38182f0d24589e7898dd4892c58c3fda58042";
const ADDRESS_PATTERN = /^0x[0-9a-fA-F]{40}$/;
const SOURCE_COMMIT_PATTERN = /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/;

function requireEnvironment(environment, name) {
  const value = environment[name]?.trim();
  if (!value) throw new Error(`${name} is required.`);
  return value;
}

function normalizeAddress(value, label) {
  if (!ADDRESS_PATTERN.test(value) || /^0x0{40}$/i.test(value)) {
    throw new Error(`${label} address is invalid.`);
  }
  return value.toLowerCase();
}

function parseInteger(value, label) {
  if (!/^(0|[1-9][0-9]*)$/.test(value)) {
    throw new Error(`${label} must be an unsigned decimal integer.`);
  }
  return BigInt(value);
}

function parseHexInteger(value, label) {
  if (!/^0x[0-9a-fA-F]+$/.test(value)) {
    throw new Error(`${label} returned invalid hexadecimal data.`);
  }
  return BigInt(value);
}

function constructorCalldata(creationBytecode, administrator, signer) {
  if (!/^0x(?:[0-9a-fA-F]{2})+$/.test(creationBytecode)) {
    throw new Error("THVProofRegistry creation bytecode is invalid.");
  }
  const encodeAddress = (address) => address.slice(2).padStart(64, "0");
  return `0x${creationBytecode.slice(2)}${encodeAddress(administrator)}${encodeAddress(signer)}`;
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
      `RPC ${method} failed: ${payload.error.message ?? "unknown error"}.`,
    );
  }
  return payload.result;
}

function assertEnvironment(environment) {
  const network = requireEnvironment(environment, "BLOCKCHAIN_NETWORK");
  const chainId = requireEnvironment(environment, "BLOCKCHAIN_CHAIN_ID");
  const rpcUrl = requireEnvironment(environment, "BLOCKCHAIN_RPC_URL");
  const sourceCommit = requireEnvironment(environment, "SOURCE_COMMIT");
  const administrator = normalizeAddress(
    requireEnvironment(environment, "ADMIN_WALLET_ADDRESS"),
    "Administrator",
  );
  const signer = normalizeAddress(
    requireEnvironment(environment, "SIGNER_WALLET_ADDRESS"),
    "Signer",
  );
  const deployer = normalizeAddress(
    requireEnvironment(environment, "EXPECTED_DEPLOYER"),
    "Deployer",
  );
  const configuredBalanceFloor = parseInteger(
    requireEnvironment(environment, "MINIMUM_DEPLOYER_BALANCE_WEI"),
    "MINIMUM_DEPLOYER_BALANCE_WEI",
  );

  if (network !== "polygon" || chainId !== "137") {
    throw new Error(
      "Direct THVProofRegistry deployment is restricted to polygon:137.",
    );
  }
  if (!rpcUrl.startsWith("https://")) {
    throw new Error("Polygon Mainnet RPC URL must use HTTPS.");
  }
  if (!SOURCE_COMMIT_PATTERN.test(sourceCommit)) {
    throw new Error("SOURCE_COMMIT must be a full lowercase Git hash.");
  }
  if (administrator !== APPROVED_ADMIN) {
    throw new Error(
      "ADMIN_WALLET_ADDRESS does not match the approved Admin wallet.",
    );
  }
  if (signer !== APPROVED_SIGNER) {
    throw new Error(
      "SIGNER_WALLET_ADDRESS does not match the approved Signer wallet.",
    );
  }
  if (deployer === administrator || deployer === signer) {
    throw new Error(
      "EXPECTED_DEPLOYER must be separate from Admin and Signer wallets.",
    );
  }
  return {
    rpcUrl,
    sourceCommit,
    administrator,
    signer,
    deployer,
    configuredBalanceFloor,
  };
}

async function readDeploymentInputs(
  root,
  sourceCommit,
  deployer,
  administrator,
  signer,
) {
  const planPath = resolve(
    root,
    "artifacts",
    "releases",
    "polygon",
    "thv-proof-registry-deployment-plan.json",
  );
  const artifactPath = resolve(
    root,
    "out",
    "THVProofRegistry.sol",
    "THVProofRegistry.json",
  );
  const [plan, artifact] = await Promise.all([
    readFile(planPath, "utf8").then(JSON.parse),
    readFile(artifactPath, "utf8").then(JSON.parse),
  ]);
  if (
    plan.contract !== "THVProofRegistry" ||
    plan.network !== "polygon" ||
    Number(plan.chainId) !== 137 ||
    plan.sourceCommit !== sourceCommit
  ) {
    throw new Error(
      "Deployment plan does not match the requested Polygon release.",
    );
  }
  if (
    String(plan.roles?.deployer).toLowerCase() !== deployer ||
    String(plan.roles?.defaultAdmin).toLowerCase() !== administrator ||
    String(plan.roles?.verifier).toLowerCase() !== signer ||
    plan.roles?.deploymentKeyRetainsRole !== false
  ) {
    throw new Error(
      "Deployment plan role separation does not match the approved configuration.",
    );
  }
  return { planPath, artifact };
}

export async function runPreflight({
  root = contractRoot,
  environment = process.env,
  fetchImpl = globalThis.fetch,
  write = (line) => process.stdout.write(line),
} = {}) {
  if (typeof fetchImpl !== "function")
    throw new Error("A fetch implementation is required.");
  const {
    rpcUrl,
    sourceCommit,
    administrator,
    signer,
    deployer,
    configuredBalanceFloor,
  } = assertEnvironment(environment);
  const { planPath, artifact } = await readDeploymentInputs(
    root,
    sourceCommit,
    deployer,
    administrator,
    signer,
  );
  const deploymentData = constructorCalldata(
    artifact.bytecode?.object,
    administrator,
    signer,
  );
  const [actualChainId, balance, gasEstimate, gasPrice] = await Promise.all([
    jsonRpc(fetchImpl, rpcUrl, "eth_chainId", []),
    jsonRpc(fetchImpl, rpcUrl, "eth_getBalance", [deployer, "latest"]),
    jsonRpc(fetchImpl, rpcUrl, "eth_estimateGas", [
      { from: deployer, data: deploymentData },
    ]),
    jsonRpc(fetchImpl, rpcUrl, "eth_gasPrice", []),
  ]);
  if (parseHexInteger(actualChainId, "eth_chainId") !== 137n) {
    throw new Error(
      `RPC chain mismatch: expected 137, received ${actualChainId}.`,
    );
  }

  const balanceWei = parseHexInteger(balance, "eth_getBalance");
  const gasEstimateValue = parseHexInteger(gasEstimate, "eth_estimateGas");
  const gasPriceWei = parseHexInteger(gasPrice, "eth_gasPrice");
  const estimatedCostWei = gasEstimateValue * gasPriceWei;
  const requiredBalanceWei = [
    configuredBalanceFloor,
    estimatedCostWei * 2n,
  ].reduce((maximum, candidate) => (candidate > maximum ? candidate : maximum));
  if (balanceWei < requiredBalanceWei) {
    throw new Error(
      `Deployer balance is below the required safety floor: need ${requiredBalanceWei} wei, have ${balanceWei} wei.`,
    );
  }

  const result = {
    chainId: 137,
    planPath,
    deployer,
    administrator,
    signer,
    balanceWei,
    gasEstimate: gasEstimateValue,
    gasPriceWei,
    estimatedCostWei,
    requiredBalanceWei,
  };
  write(`THVProofRegistry Polygon preflight passed for ${result.deployer}\n`);
  write(`estimatedDeploymentCostWei=${result.estimatedCostWei}\n`);
  write(`requiredBalanceWei=${result.requiredBalanceWei}\n`);
  return result;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  runPreflight().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
