import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const POLYGON_MAINNET_CHAIN_ID = 137;
const ADDRESS_PATTERN = /^0x[0-9a-fA-F]{40}$/;
const TRANSACTION_HASH_PATTERN = /^0x[0-9a-fA-F]{64}$/;

function isProofRegistry(contractName) {
  return (
    typeof contractName === "string" &&
    contractName.split(/[\\/:]/).at(-1) === "THVProofRegistry"
  );
}

function parseChainId(value) {
  if (typeof value === "number" && Number.isSafeInteger(value)) return value;
  if (typeof value === "string" && /^0x[0-9a-fA-F]+$/.test(value)) {
    return Number.parseInt(value, 16);
  }
  if (typeof value === "string" && /^(0|[1-9][0-9]*)$/.test(value)) {
    return Number.parseInt(value, 10);
  }
  throw new Error("transaction chainId is invalid");
}

export function parseMainnetBroadcastEvidence(broadcast, expectedDeployer) {
  if (!ADDRESS_PATTERN.test(expectedDeployer)) {
    throw new Error("EXPECTED_DEPLOYER is invalid");
  }
  if (!broadcast || typeof broadcast !== "object") {
    throw new Error("broadcast evidence is invalid");
  }
  if (Number(broadcast.chain) !== POLYGON_MAINNET_CHAIN_ID) {
    throw new Error("broadcast evidence chain is not 137");
  }

  const deployments = (
    Array.isArray(broadcast.transactions) ? broadcast.transactions : []
  ).filter(
    (transaction) =>
      transaction &&
      typeof transaction === "object" &&
      transaction.transactionType === "CREATE" &&
      isProofRegistry(transaction.contractName),
  );
  if (deployments.length !== 1) {
    throw new Error(
      `expected exactly one THVProofRegistry CREATE, found ${deployments.length}`,
    );
  }

  const deployment = deployments[0];
  if (!ADDRESS_PATTERN.test(deployment.contractAddress)) {
    throw new Error("deployment address is invalid");
  }
  if (!TRANSACTION_HASH_PATTERN.test(deployment.hash)) {
    throw new Error("deployment transaction hash is invalid");
  }
  const from = deployment.transaction?.from ?? deployment.from;
  if (!ADDRESS_PATTERN.test(from)) {
    throw new Error("deployment sender evidence is missing or invalid");
  }
  if (from.toLowerCase() !== expectedDeployer.toLowerCase()) {
    throw new Error("deployment sender does not match EXPECTED_DEPLOYER");
  }
  const transactionChainId =
    deployment.transaction?.chainId ?? deployment.chainId;
  if (
    transactionChainId !== undefined &&
    parseChainId(transactionChainId) !== POLYGON_MAINNET_CHAIN_ID
  ) {
    throw new Error("deployment transaction chainId is not 137");
  }

  return {
    contractAddress: deployment.contractAddress.toLowerCase(),
    transactionHash: deployment.hash.toLowerCase(),
  };
}

export async function readMainnetBroadcastEvidence({
  evidencePath,
  expectedDeployer,
  readFileImpl = readFile,
} = {}) {
  if (!evidencePath) throw new Error("broadcast evidence path is required");
  const broadcast = JSON.parse(await readFileImpl(evidencePath, "utf8"));
  return parseMainnetBroadcastEvidence(broadcast, expectedDeployer);
}

export async function runCli({
  argv = process.argv.slice(2),
  readFileImpl = readFile,
  write = (value) => process.stdout.write(value),
} = {}) {
  if (argv.length !== 2) {
    throw new Error(
      "Usage: read-thv-proof-registry-mainnet-broadcast-evidence.mjs <evidence-path> <expected-deployer>",
    );
  }
  const [evidencePath, expectedDeployer] = argv;
  const { contractAddress } = await readMainnetBroadcastEvidence({
    evidencePath,
    expectedDeployer,
    readFileImpl,
  });
  write(contractAddress);
  return contractAddress;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  runCli().catch((error) => {
    process.stderr.write(
      `Incompatible prior Mainnet broadcast evidence: ${error.message}\n`,
    );
    process.exitCode = 70;
  });
}
