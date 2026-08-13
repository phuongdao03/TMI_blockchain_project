import { mkdir, readFile, writeFile } from "node:fs/promises";
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
const sourceCommit = options.get("source-commit");
const deployer = options.get("deployer");
const administrator = options.get("administrator");
const issuer = options.get("issuer");
const addressPattern = /^0x[0-9a-fA-F]{40}$/;

if (!sourceCommit || !/^[0-9a-f]{40}(?:[0-9a-f]{24})?$/.test(sourceCommit)) {
  throw new Error("Source commit must be a full lowercase Git hash.");
}
for (const [name, value] of Object.entries({
  deployer,
  administrator,
  issuer,
})) {
  if (!value || !addressPattern.test(value) || /^0x0{40}$/i.test(value)) {
    throw new Error(`${name} address is invalid.`);
  }
}
if (administrator.toLowerCase() === issuer.toLowerCase()) {
  throw new Error("Administrator and issuer must use separate identities.");
}

const qualifiedManifestPath = resolve(
  root,
  options.get("qualified-manifest") ?? "artifacts/releases/amoy/manifest.json",
);
const qualified = JSON.parse(await readFile(qualifiedManifestPath, "utf8"));
if (qualified.network !== "amoy" || Number(qualified.chainId) !== 80_002) {
  throw new Error("Qualified release must come from Amoy chain 80002.");
}
if (qualified.sourceCommit !== sourceCommit) {
  throw new Error("Source commit differs from the qualified Amoy release.");
}
if (
  !qualified.bytecode?.creationSha256 ||
  !qualified.bytecode?.runtimeSha256 ||
  !qualified.abiSha256 ||
  !qualified.compiler
) {
  throw new Error("Qualified release provenance is incomplete.");
}

const plan = {
  schemaVersion: 1,
  mode: "dry-run",
  network: "polygon",
  chainId: 137,
  sourceCommit,
  qualifiedAmoyRelease: {
    manifest: "../amoy/manifest.json",
    abiSha256: qualified.abiSha256,
  },
  compiler: qualified.compiler,
  bytecode: qualified.bytecode,
  roles: {
    deployer,
    administrator,
    pauser: administrator,
    issuer,
  },
  ownership: {
    defaultAdmin: administrator,
    deploymentKeyRetainsRole: false,
  },
  deploymentCommand:
    "forge script script/DeployCertificateRegistry.s.sol --chain 137 --broadcast",
  verificationCommand:
    "forge verify-contract <address> src/CertificateRegistry.sol:CertificateRegistry --chain 137 --watch",
};
const outputPath = resolve(
  root,
  "artifacts/releases/polygon/dry-run-plan.json",
);
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(plan, null, 2)}\n`);
console.log(outputPath);
