#!/usr/bin/env bash
set -euo pipefail

# Mainnet retry semantics are deliberately fail-closed. If Foundry left prior
# broadcast evidence, this script validates its chain, deployer, address, and
# on-chain runtime bytecode before reusing it for postflight. It never sends a
# second CREATE while incompatible evidence is present.
readonly MAINNET_BROADCAST_EVIDENCE_PATH="broadcast/DeployTHVProofRegistry.s.sol/137/run-latest.json"

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--confirm-mainnet]" >&2
  exit 64
fi

: "${BLOCKCHAIN_NETWORK:?BLOCKCHAIN_NETWORK is required}"
: "${BLOCKCHAIN_CHAIN_ID:?BLOCKCHAIN_CHAIN_ID is required}"
: "${BLOCKCHAIN_RPC_URL:?BLOCKCHAIN_RPC_URL is required}"
: "${ADMIN_WALLET_ADDRESS:?ADMIN_WALLET_ADDRESS is required}"
: "${SIGNER_WALLET_ADDRESS:?SIGNER_WALLET_ADDRESS is required}"
: "${EXPECTED_DEPLOYER:?EXPECTED_DEPLOYER is required}"

read_prior_broadcast_address() {
  local evidence_path="$1"
  local expected_deployer="$2"

  node scripts/read-thv-proof-registry-mainnet-broadcast-evidence.mjs \
    "$evidence_path" \
    "$expected_deployer"
}

read_compiled_runtime_code() {
  node -e '
const artifact = require("./out/THVProofRegistry.sol/THVProofRegistry.json");
const runtimeCode = artifact.deployedBytecode?.object;
if (!/^0x(?:[0-9a-fA-F]{2})+$/.test(runtimeCode ?? "")) {
  throw new Error("THVProofRegistry compiled runtime bytecode is invalid.");
}
process.stdout.write(runtimeCode.toLowerCase());
'
}

assert_runtime_code_matches_artifact() {
  local registry_address="$1"
  local expected_runtime_code="$2"
  local deployed_runtime_code

  if ! deployed_runtime_code="$(cast code "$registry_address" --rpc-url "$BLOCKCHAIN_RPC_URL" | tr '[:upper:]' '[:lower:]' | tr -d '\r\n')"; then
    echo "Unable to read THVProofRegistry runtime bytecode from Polygon Mainnet." >&2
    exit 70
  fi
  if [[ "$deployed_runtime_code" != "$expected_runtime_code" ]]; then
    echo "THVProofRegistry runtime bytecode does not match the immutable release artifact." >&2
    exit 70
  fi
}

run_mainnet_postflight() {
  local registry_address="$1"
  local expected_runtime_code="$2"
  local manifest_address
  local constructor_args

  assert_runtime_code_matches_artifact "$registry_address" "$expected_runtime_code"
  node scripts/export-thv-proof-registry-artifacts.mjs \
    --network=polygon \
    --chain-id=137 \
    --source-commit="$SOURCE_COMMIT"
  if ! manifest_address="$(node -e '
const manifest = require("./artifacts/releases/polygon/thv-proof-registry-manifest.json");
const address = manifest.proofRegistry;
if (!/^0x[0-9a-fA-F]{40}$/.test(address ?? "")) {
  throw new Error("Mainnet manifest proofRegistry address is invalid.");
}
process.stdout.write(address.toLowerCase());
')"; then
    echo "Unable to read THVProofRegistry address from Mainnet release manifest." >&2
    exit 70
  fi
  if [[ "$manifest_address" != "$registry_address" ]]; then
    echo "Mainnet release manifest address does not match broadcast evidence." >&2
    exit 70
  fi

  THV_PROOF_REGISTRY_CONTRACT_ADDRESS="$registry_address" \
    node scripts/verify-thv-proof-registry-roles.mjs
  constructor_args="$(cast abi-encode 'constructor(address,address)' "$ADMIN_WALLET_ADDRESS" "$SIGNER_WALLET_ADDRESS")"
  forge verify-contract "$registry_address" src/THVProofRegistry.sol:THVProofRegistry \
    --chain 137 \
    --watch \
    --verifier etherscan \
    --etherscan-api-key "$POLYGONSCAN_API_KEY" \
    --constructor-args "$constructor_args"
}

case "$BLOCKCHAIN_NETWORK:$BLOCKCHAIN_CHAIN_ID" in
  local:31337|amoy:80002|polygon:137) ;;
  *)
    echo "Invalid network/chain pair: $BLOCKCHAIN_NETWORK:$BLOCKCHAIN_CHAIN_ID" >&2
    exit 65
    ;;
esac

if [[ "$BLOCKCHAIN_NETWORK" != "local" && "$BLOCKCHAIN_RPC_URL" != https://* ]]; then
  echo "Amoy and Polygon RPC URLs must use HTTPS." >&2
  exit 65
fi

actual_chain_id="$(cast chain-id --rpc-url "$BLOCKCHAIN_RPC_URL")"
if [[ "$actual_chain_id" != "$BLOCKCHAIN_CHAIN_ID" ]]; then
  echo "RPC chain mismatch: expected $BLOCKCHAIN_CHAIN_ID, received $actual_chain_id." >&2
  exit 65
fi

if [[ "$BLOCKCHAIN_NETWORK" == "local" ]]; then
  : "${DEPLOYER_ADDRESS:?DEPLOYER_ADDRESS is required for Anvil}"
  forge script script/DeployTHVProofRegistry.s.sol:DeployTHVProofRegistry \
    --rpc-url "$BLOCKCHAIN_RPC_URL" \
    --broadcast \
    --unlocked \
    --sender "$DEPLOYER_ADDRESS"
  exit 0
fi

if [[ "$BLOCKCHAIN_NETWORK" == "polygon" ]]; then
  : "${POLYGONSCAN_API_KEY:?POLYGONSCAN_API_KEY is required for Mainnet source verification}"
  : "${SOURCE_COMMIT:?SOURCE_COMMIT is required for an immutable Mainnet release}"
  if [[ "${1:-}" != "--confirm-mainnet" ]]; then
    echo "Polygon deployment requires the explicit --confirm-mainnet argument." >&2
    exit 65
  fi
  if [[ "${MAINNET_DEPLOY_CONFIRMATION:-}" != "DEPLOY_THV_PROOF_REGISTRY_TO_POLYGON_MAINNET" ]]; then
    echo "MAINNET_DEPLOY_CONFIRMATION is missing or invalid." >&2
    exit 65
  fi
  if [[ "${THV_PROOF_REGISTRY_TEST_MODE:-false}" != "false" ]]; then
    echo "THV_PROOF_REGISTRY_TEST_MODE must be false for Polygon Mainnet." >&2
    exit 65
  fi

  for command_name in forge cast node git npm; do
    command -v "$command_name" >/dev/null 2>&1 || {
      echo "Required command is unavailable: $command_name" >&2
      exit 69
    }
  done

  # These commands are read-only until the final forge script invocation below.
  npm ci --ignore-scripts
  forge build --force
  forge test --match-contract '^(THVProofRegistryTest|DeployTHVProofRegistryTest)$'
  node scripts/create-thv-proof-registry-mainnet-plan.mjs \
    --source-commit="$SOURCE_COMMIT" \
    --deployer="$EXPECTED_DEPLOYER" \
    --administrator="$ADMIN_WALLET_ADDRESS" \
    --signer="$SIGNER_WALLET_ADDRESS"

  expected_runtime_code="$(read_compiled_runtime_code)"
  if [[ -e "$MAINNET_BROADCAST_EVIDENCE_PATH" ]]; then
    if ! registry_address="$(read_prior_broadcast_address "$MAINNET_BROADCAST_EVIDENCE_PATH" "$EXPECTED_DEPLOYER")"; then
      echo "Refusing Mainnet broadcast because prior evidence is incompatible." >&2
      exit 70
    fi
    assert_runtime_code_matches_artifact "$registry_address" "$expected_runtime_code"
    printf 'Resuming THVProofRegistry Mainnet postflight from prior broadcast evidence at %s\n' "$registry_address"
    run_mainnet_postflight "$registry_address" "$expected_runtime_code"
    printf 'THVProofRegistry Mainnet postflight completed at %s\n' "$registry_address"
    exit 0
  fi

  : "${DEPLOYER_PRIVATE_KEY:?DEPLOYER_PRIVATE_KEY is required only for the deployment operator}"
  if [[ ! "$DEPLOYER_PRIVATE_KEY" =~ ^0x[0-9a-fA-F]{64}$ ]]; then
    echo "DEPLOYER_PRIVATE_KEY must be 0x-prefixed 32-byte hexadecimal data." >&2
    exit 65
  fi
  : "${MINIMUM_DEPLOYER_BALANCE_WEI:?MINIMUM_DEPLOYER_BALANCE_WEI is required}"
  node scripts/preflight-thv-proof-registry-mainnet.mjs

  if ! forge script script/DeployTHVProofRegistry.s.sol:DeployTHVProofRegistry \
    --chain 137 \
    --rpc-url "$BLOCKCHAIN_RPC_URL" \
    --broadcast; then
    echo "Mainnet broadcast invocation failed. Do not remove broadcast evidence; rerun this command to perform fail-closed resume detection." >&2
    exit 70
  fi

  if ! registry_address="$(read_prior_broadcast_address "$MAINNET_BROADCAST_EVIDENCE_PATH" "$EXPECTED_DEPLOYER")"; then
    echo "Broadcast returned without valid THVProofRegistry evidence; refusing any automatic retry." >&2
    exit 70
  fi
  run_mainnet_postflight "$registry_address" "$expected_runtime_code"
  printf 'THVProofRegistry deployed and verified at %s\n' "$registry_address"
  exit 0
fi

: "${DEPLOYER_PRIVATE_KEY:?DEPLOYER_PRIVATE_KEY is required only for the deployment operator}"
if [[ ! "$DEPLOYER_PRIVATE_KEY" =~ ^0x[0-9a-fA-F]{64}$ ]]; then
  echo "DEPLOYER_PRIVATE_KEY must be 0x-prefixed 32-byte hexadecimal data." >&2
  exit 65
fi

forge script script/DeployTHVProofRegistry.s.sol:DeployTHVProofRegistry \
  --rpc-url "$BLOCKCHAIN_RPC_URL" \
  --broadcast
