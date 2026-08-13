import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const options = new Map(
  process.argv.slice(2).map((argument) => {
    const [key, value] = argument.split("=", 2);
    return [key.replace(/^--/, ""), value];
  }),
);
const root = resolve(options.get("root") ?? scriptRoot);
const network = options.get("network");
const chainId = Number(options.get("chain-id"));
const allowedNetworks = new Map([
  ["local", 31_337],
  ["amoy", 80_002],
]);

if (!network || allowedNetworks.get(network) !== chainId) {
  throw new Error("Network and chain-id must match local:31337 or amoy:80002.");
}

function sha256HexBytes(bytecode) {
  if (!/^0x(?:[0-9a-fA-F]{2})+$/.test(bytecode)) {
    throw new Error(
      "Contract bytecode must be non-empty, even-length hexadecimal data.",
    );
  }
  return `0x${createHash("sha256")
    .update(Buffer.from(bytecode.slice(2), "hex"))
    .digest("hex")}`;
}

function sha256Utf8(value) {
  return `0x${createHash("sha256").update(value, "utf8").digest("hex")}`;
}

function resolveSourceCommit() {
  const supplied = options.get("source-commit") ?? process.env.SOURCE_COMMIT;
  const commit =
    supplied ??
    execFileSync("git", ["rev-parse", "HEAD"], {
      cwd: root,
      encoding: "utf8",
    }).trim();
  if (!/^[0-9a-f]{40}(?:[0-9a-f]{24})?$/.test(commit)) {
    throw new Error(
      "Source commit must be a full 40 or 64 character lowercase Git hash.",
    );
  }
  return commit;
}

const contractArtifactPath = resolve(
  root,
  "out",
  "CertificateRegistry.sol",
  "CertificateRegistry.json",
);
const broadcastPath = resolve(
  root,
  options.get("broadcast") ??
    `broadcast/DeployCertificateRegistry.s.sol/${chainId}/run-latest.json`,
);
const artifact = JSON.parse(await readFile(contractArtifactPath, "utf8"));
const broadcast = JSON.parse(await readFile(broadcastPath, "utf8"));
if (broadcast.chain !== undefined && Number(broadcast.chain) !== chainId) {
  throw new Error(
    "Broadcast chain does not match the requested release chain.",
  );
}
function isCertificateRegistry(contractName) {
  return (
    typeof contractName === "string" &&
    contractName.split(/[\\/:]/).at(-1) === "CertificateRegistry"
  );
}
const deployment = broadcast.transactions.find(
  (transaction) =>
    transaction.transactionType === "CREATE" &&
    isCertificateRegistry(transaction.contractName),
);
if (!deployment?.contractAddress || !deployment.hash) {
  throw new Error("CertificateRegistry deployment was not found.");
}
if (!/^0x[0-9a-fA-F]{40}$/.test(deployment.contractAddress)) {
  throw new Error("Deployment address is invalid.");
}
if (!/^0x[0-9a-fA-F]{64}$/.test(deployment.hash)) {
  throw new Error("Deployment transaction hash is invalid.");
}

const metadata =
  typeof artifact.metadata === "string"
    ? JSON.parse(artifact.metadata)
    : artifact.metadata;
if (!metadata?.compiler?.version || !metadata.settings) {
  throw new Error(
    "Compiler version and settings are missing from the Foundry artifact.",
  );
}
const creationBytecode = artifact.bytecode?.object;
const runtimeBytecode = artifact.deployedBytecode?.object;
const normalizedAbi = `${JSON.stringify(artifact.abi, null, 2)}\n`;
const sourceCommit = resolveSourceCommit();
const releaseDirectory = resolve(root, "artifacts", "releases", network);
const abiPath = resolve(root, "artifacts", "CertificateRegistry.abi.json");
const releaseAbiPath = resolve(
  releaseDirectory,
  "CertificateRegistry.abi.json",
);
const manifestPath = resolve(releaseDirectory, "manifest.json");
const deploymentManifestPath = resolve(root, "deployments", `${network}.json`);
const manifest = {
  schemaVersion: 1,
  network,
  chainId,
  sourceCommit,
  certificateRegistry: deployment.contractAddress,
  deploymentTransactionHash: deployment.hash,
  compiler: {
    version: metadata.compiler.version,
    settings: metadata.settings,
  },
  abi: "CertificateRegistry.abi.json",
  abiSha256: sha256Utf8(normalizedAbi),
  bytecode: {
    creationSha256: sha256HexBytes(creationBytecode),
    runtimeSha256: sha256HexBytes(runtimeBytecode),
  },
};

await mkdir(dirname(abiPath), { recursive: true });
await mkdir(releaseDirectory, { recursive: true });
await mkdir(dirname(deploymentManifestPath), { recursive: true });
await Promise.all([
  writeFile(abiPath, normalizedAbi),
  writeFile(releaseAbiPath, normalizedAbi),
  writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`),
  writeFile(
    deploymentManifestPath,
    `${JSON.stringify(
      {
        network,
        chainId,
        certificateRegistry: deployment.contractAddress,
        deploymentTransactionHash: deployment.hash,
        releaseManifest: `../artifacts/releases/${network}/manifest.json`,
        abi: "../artifacts/CertificateRegistry.abi.json",
      },
      null,
      2,
    )}\n`,
  ),
]);
