import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const options = new Map(
  process.argv.slice(2).map((argument) => {
    const [key, value] = argument.split("=", 2);
    return [key.replace(/^--/, ""), value];
  }),
);
const network = options.get("network");
const chainId = Number(options.get("chain-id"));
const allowedNetworks = new Map([
  ["local", 31_337],
  ["amoy", 80_002],
]);
if (!network || allowedNetworks.get(network) !== chainId) {
  throw new Error("Network and chain-id must match local:31337 or amoy:80002.");
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
const deployment = broadcast.transactions.find(
  (transaction) =>
    transaction.transactionType === "CREATE" &&
    transaction.contractName === "CertificateRegistry",
);
if (!deployment?.contractAddress) {
  throw new Error("CertificateRegistry deployment was not found.");
}
if (!/^0x[0-9a-fA-F]{40}$/.test(deployment.contractAddress)) {
  throw new Error("Deployment address is invalid.");
}

const abiPath = resolve(root, "artifacts", "CertificateRegistry.abi.json");
const manifestPath = resolve(root, "deployments", `${network}.json`);
await mkdir(dirname(abiPath), { recursive: true });
await mkdir(dirname(manifestPath), { recursive: true });
await writeFile(abiPath, `${JSON.stringify(artifact.abi, null, 2)}\n`);
await writeFile(
  manifestPath,
  `${JSON.stringify(
    {
      network,
      chainId,
      certificateRegistry: deployment.contractAddress,
      deploymentTransactionHash: deployment.hash,
      abi: "../artifacts/CertificateRegistry.abi.json",
    },
    null,
    2,
  )}\n`,
);
