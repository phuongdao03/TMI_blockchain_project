import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const contractRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const APPROVED_ADMIN = "0xec5fcdFab3FCafCEFCED55CC702CD3B13f54B4Fe".toLowerCase();
const APPROVED_SIGNER = "0xbfa38182f0d24589e7898dd4892c58c3fda58042";
const ADDRESS_PATTERN = /^0x[0-9a-fA-F]{40}$/;
const SOURCE_COMMIT_PATTERN = /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/;
const RELEASE_INPUTS = [
  "foundry.toml",
  "package.json",
  "package-lock.json",
  "src/THVProofRegistry.sol",
  "script/DeployTHVProofRegistry.s.sol",
  "test/THVProofRegistry.t.sol",
  "test/DeployTHVProofRegistry.t.sol",
  "scripts/deploy-thv-proof-registry.sh",
  "scripts/read-thv-proof-registry-mainnet-broadcast-evidence.mjs",
  "scripts/verify-thv-proof-registry-roles.mjs",
  "scripts/create-thv-proof-registry-mainnet-plan.mjs",
  "scripts/preflight-thv-proof-registry-mainnet.mjs",
  "scripts/export-thv-proof-registry-artifacts.mjs",
  "artifacts/THVProofRegistry.abi.json",
];

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
    throw new Error("Contract bytecode must be non-empty, even-length hexadecimal data.");
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

function normalizeAddress(value, label) {
  if (!value || !ADDRESS_PATTERN.test(value) || /^0x0{40}$/i.test(value)) {
    throw new Error(`${label} address is invalid.`);
  }
  return value.toLowerCase();
}

function assertApprovedRoles({ administrator, signer, deployer }) {
  if (administrator !== APPROVED_ADMIN) {
    throw new Error("ADMIN_WALLET_ADDRESS does not match the approved Admin wallet.");
  }
  if (signer !== APPROVED_SIGNER) {
    throw new Error("SIGNER_WALLET_ADDRESS does not match the approved Signer wallet.");
  }
  if (deployer === administrator || deployer === signer) {
    throw new Error("Deployer wallet must be separate from Admin and Signer wallets.");
  }
}

function git(root, argumentsList) {
  return execFileSync("git", argumentsList, { cwd: root, encoding: "utf8" }).trim();
}

function assertImmutableSource(root, sourceCommit) {
  const head = git(root, ["rev-parse", "HEAD"]);
  if (head !== sourceCommit) {
    throw new Error("SOURCE_COMMIT must match the checked-out immutable release commit.");
  }
  git(root, ["cat-file", "-e", `${sourceCommit}^{commit}`]);
  for (const input of RELEASE_INPUTS) {
    try {
      git(root, ["ls-files", "--error-unmatch", "--", input]);
    } catch {
      throw new Error(`Release input is not tracked by SOURCE_COMMIT: ${input}`);
    }
  }
  for (const argumentsList of [
    ["diff", "--quiet", "--", ...RELEASE_INPUTS],
    ["diff", "--cached", "--quiet", "--", ...RELEASE_INPUTS],
  ]) {
    try {
      git(root, argumentsList);
    } catch {
      throw new Error("Release inputs must not have uncommitted changes.");
    }
  }
  const status = git(root, ["status", "--porcelain", "--untracked-files=all", "--", ...RELEASE_INPUTS]);
  if (status) {
    throw new Error("Release inputs must not have staged, unstaged, or untracked changes.");
  }
}

const options = parseOptions(process.argv.slice(2));
const root = resolve(options.get("root") ?? contractRoot);
const sourceCommit = options.get("source-commit") ?? process.env.SOURCE_COMMIT;
const deployer = normalizeAddress(options.get("deployer") ?? process.env.EXPECTED_DEPLOYER, "Deployer");
const administrator = normalizeAddress(
  options.get("administrator") ?? process.env.ADMIN_WALLET_ADDRESS,
  "Administrator",
);
const signer = normalizeAddress(options.get("signer") ?? process.env.SIGNER_WALLET_ADDRESS, "Signer");

if (!sourceCommit || !SOURCE_COMMIT_PATTERN.test(sourceCommit)) {
  throw new Error("SOURCE_COMMIT must be a full lowercase Git hash.");
}
assertApprovedRoles({ administrator, signer, deployer });
assertImmutableSource(root, sourceCommit);

const artifactPath = resolve(root, "out", "THVProofRegistry.sol", "THVProofRegistry.json");
const artifact = JSON.parse(await readFile(artifactPath, "utf8"));
const metadata =
  typeof artifact.metadata === "string" ? JSON.parse(artifact.metadata) : artifact.metadata;
if (!Array.isArray(artifact.abi) || !metadata?.compiler?.version || !metadata.settings) {
  throw new Error("THVProofRegistry artifact is missing ABI, compiler version, or compiler settings.");
}

const creationBytecode = artifact.bytecode?.object;
const runtimeBytecode = artifact.deployedBytecode?.object;
const plan = {
  schemaVersion: 1,
  releaseType: "direct-mainnet",
  contract: "THVProofRegistry",
  network: "polygon",
  chainId: 137,
  sourceCommit,
  artifact: {
    path: "out/THVProofRegistry.sol/THVProofRegistry.json",
    sha256: sha256Json(artifact),
    abiSha256: sha256Json(artifact.abi),
  },
  compiler: {
    version: metadata.compiler.version,
    settings: metadata.settings,
  },
  bytecode: {
    creationSha256: sha256Bytes(creationBytecode),
    runtimeSha256: sha256Bytes(runtimeBytecode),
  },
  constructor: {
    administrator: "0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe",
    signer: "0xBfA38182f0D24589e7898DD4892C58c3FDa58042",
  },
  roles: {
    deployer,
    defaultAdmin: "0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe",
    verifier: "0xBfA38182f0D24589e7898DD4892C58c3FDa58042",
    deploymentKeyRetainsRole: false,
  },
  requiredEnvironment: [
    "BLOCKCHAIN_NETWORK=polygon",
    "BLOCKCHAIN_CHAIN_ID=137",
    "BLOCKCHAIN_RPC_URL",
    "ADMIN_WALLET_ADDRESS",
    "SIGNER_WALLET_ADDRESS",
    "EXPECTED_DEPLOYER",
    "DEPLOYER_PRIVATE_KEY",
    "POLYGONSCAN_API_KEY",
  ],
  deploymentCommand:
    "bash scripts/deploy-thv-proof-registry.sh --confirm-mainnet",
  verificationCommand:
    "forge verify-contract <contract-address> src/THVProofRegistry.sol:THVProofRegistry --chain 137 --watch",
};

const outputPath = resolve(
  root,
  "artifacts",
  "releases",
  "polygon",
  "thv-proof-registry-deployment-plan.json",
);
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(plan, null, 2)}\n`);
console.log(outputPath);
