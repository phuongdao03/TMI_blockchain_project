import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const contractRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const options = new Map(
  process.argv.slice(2).map((argument) => {
    const [key, value] = argument.split("=", 2);
    return [key.replace(/^--/, ""), value];
  }),
);
const root = resolve(options.get("root") ?? contractRoot);
const network = options.get("network");
const chainId = Number(options.get("chain-id"));
const address = options.get("address");
const explorerBaseUrl = options.get("explorer-base-url");
const sourceCommit = options.get("source-commit");

if (network !== "amoy" || chainId !== 80_002) {
  throw new Error("Explorer evidence is restricted to Amoy chain 80002.");
}
if (!address || !/^0x[0-9a-fA-F]{40}$/.test(address)) {
  throw new Error("Verified contract address is invalid.");
}
if (explorerBaseUrl !== "https://amoy.polygonscan.com") {
  throw new Error("Explorer base URL is not allowlisted.");
}
if (!sourceCommit || !/^[0-9a-f]{40}(?:[0-9a-f]{24})?$/.test(sourceCommit)) {
  throw new Error("Source commit must be a full lowercase Git hash.");
}

const manifestPath = resolve(root, "artifacts/releases/amoy/manifest.json");
const evidencePath = resolve(
  root,
  "artifacts/releases/amoy/explorer-evidence.json",
);
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
if (
  manifest.network !== network ||
  Number(manifest.chainId) !== chainId ||
  manifest.sourceCommit !== sourceCommit ||
  manifest.certificateRegistry.toLowerCase() !== address.toLowerCase()
) {
  throw new Error("Explorer evidence does not match the release manifest.");
}

const evidence = {
  schemaVersion: 1,
  network,
  chainId,
  sourceCommit,
  certificateRegistry: address,
  deploymentTransactionHash: manifest.deploymentTransactionHash,
  verificationProvider: "polygonscan",
  verificationStatus: "verified",
  contractUrl: `${explorerBaseUrl}/address/${address}#code`,
};

await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);
console.log(evidencePath);
