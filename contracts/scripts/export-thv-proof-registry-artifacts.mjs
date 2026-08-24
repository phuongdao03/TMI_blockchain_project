import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const contractRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE_COMMIT_PATTERN = /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/;
const ADDRESS_PATTERN = /^0x[0-9a-fA-F]{40}$/;
const TRANSACTION_HASH_PATTERN = /^0x[0-9a-fA-F]{64}$/;

function parseOptions(argumentsList) {
  return new Map(
    argumentsList.map((argument) => {
      const [rawKey, ...rawValue] = argument.split("=");
      return [rawKey.replace(/^--/, ""), rawValue.join("=")];
    }),
  );
}

function sha256Bytes(value) {
  if (!/^0x(?:[0-9a-fA-F]{2})+$/.test(value)) {
    throw new Error(
      "Contract bytecode must be non-empty, even-length hexadecimal data.",
    );
  }
  return `0x${createHash("sha256")
    .update(Buffer.from(value.slice(2), "hex"))
    .digest("hex")}`;
}

function sha256Json(value) {
  return `0x${createHash("sha256")
    .update(`${JSON.stringify(value, null, 2)}\n`, "utf8")
    .digest("hex")}`;
}

function isProofRegistry(contractName) {
  return (
    typeof contractName === "string" &&
    contractName.split(/[\\/:]/).at(-1) === "THVProofRegistry"
  );
}

const options = parseOptions(process.argv.slice(2));
const root = resolve(options.get("root") ?? contractRoot);
const network = options.get("network");
const chainId = Number(options.get("chain-id"));
const sourceCommit = options.get("source-commit") ?? process.env.SOURCE_COMMIT;
if (network !== "polygon" || chainId !== 137) {
  throw new Error(
    "THVProofRegistry release export is restricted to polygon:137.",
  );
}
if (!sourceCommit || !SOURCE_COMMIT_PATTERN.test(sourceCommit)) {
  throw new Error("SOURCE_COMMIT must be a full lowercase Git hash.");
}

const artifactPath = resolve(
  root,
  "out",
  "THVProofRegistry.sol",
  "THVProofRegistry.json",
);
const broadcastPath = resolve(
  root,
  options.get("broadcast") ??
    "broadcast/DeployTHVProofRegistry.s.sol/137/run-latest.json",
);
const planPath = resolve(
  root,
  "artifacts",
  "releases",
  "polygon",
  "thv-proof-registry-deployment-plan.json",
);
const [artifact, broadcast, plan] = await Promise.all([
  readFile(artifactPath, "utf8").then(JSON.parse),
  readFile(broadcastPath, "utf8").then(JSON.parse),
  readFile(planPath, "utf8").then(JSON.parse),
]);
if (Number(broadcast.chain) !== chainId) {
  throw new Error(
    "Broadcast chain does not match the requested release chain.",
  );
}
if (
  plan.contract !== "THVProofRegistry" ||
  plan.network !== network ||
  Number(plan.chainId) !== chainId ||
  plan.sourceCommit !== sourceCommit
) {
  throw new Error(
    "Deployment plan does not match the requested release export.",
  );
}
const deployment = broadcast.transactions?.find(
  (transaction) =>
    transaction.transactionType === "CREATE" &&
    isProofRegistry(transaction.contractName),
);
if (!deployment?.contractAddress || !deployment.hash) {
  throw new Error(
    "THVProofRegistry deployment was not found in broadcast evidence.",
  );
}
if (!ADDRESS_PATTERN.test(deployment.contractAddress)) {
  throw new Error("Deployment address is invalid.");
}
if (!TRANSACTION_HASH_PATTERN.test(deployment.hash)) {
  throw new Error("Deployment transaction hash is invalid.");
}

const metadata =
  typeof artifact.metadata === "string"
    ? JSON.parse(artifact.metadata)
    : artifact.metadata;
if (
  !Array.isArray(artifact.abi) ||
  !metadata?.compiler?.version ||
  !metadata.settings
) {
  throw new Error("THVProofRegistry artifact provenance is incomplete.");
}
const normalizedAbi = `${JSON.stringify(artifact.abi, null, 2)}\n`;
const releaseDirectory = resolve(root, "artifacts", "releases", network);
const abiPath = resolve(root, "artifacts", "THVProofRegistry.abi.json");
const releaseAbiPath = resolve(releaseDirectory, "THVProofRegistry.abi.json");
const manifestPath = resolve(
  releaseDirectory,
  "thv-proof-registry-manifest.json",
);
const manifest = {
  schemaVersion: 1,
  contract: "THVProofRegistry",
  network,
  chainId,
  sourceCommit,
  proofRegistry: deployment.contractAddress,
  deploymentTransactionHash: deployment.hash,
  compiler: {
    version: metadata.compiler.version,
    settings: metadata.settings,
  },
  abi: "THVProofRegistry.abi.json",
  abiSha256: sha256Json(artifact.abi),
  bytecode: {
    creationSha256: sha256Bytes(artifact.bytecode?.object),
    runtimeSha256: sha256Bytes(artifact.deployedBytecode?.object),
  },
  roles: plan.roles,
  deploymentPlanSha256: sha256Json(plan),
};

await mkdir(dirname(abiPath), { recursive: true });
await mkdir(releaseDirectory, { recursive: true });
await Promise.all([
  writeFile(abiPath, normalizedAbi),
  writeFile(releaseAbiPath, normalizedAbi),
  writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`),
]);
console.log(manifestPath);
