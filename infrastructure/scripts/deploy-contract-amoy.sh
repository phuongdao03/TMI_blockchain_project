#!/bin/bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

required() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required environment variable: %s\n' "$name" >&2
    exit 1
  fi
}

for command_name in cast forge git node; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command is unavailable: %s\n' "$command_name" >&2
    exit 1
  }
done

for variable_name in \
  AMOY_RPC_URL \
  DEPLOYER_PRIVATE_KEY \
  EXPECTED_DEPLOYER \
  CONTRACT_ADMIN \
  EXPECTED_CONTRACT_ADMIN \
  ISSUER_ADDRESS \
  EXPECTED_ISSUER \
  POLYGONSCAN_API_KEY; do
  required "$variable_name"
done

if [[ ! "$AMOY_RPC_URL" =~ ^https:// ]]; then
  printf '%s\n' 'AMOY_RPC_URL must use HTTPS.' >&2
  exit 1
fi

chain_id="$(cast chain-id --rpc-url "$AMOY_RPC_URL")"
if [[ "$chain_id" != "80002" ]]; then
  printf 'Refusing deployment: expected Amoy chain 80002, received %s.\n' "$chain_id" >&2
  exit 1
fi

actual_deployer="$(cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY")"
if [[ "${actual_deployer,,}" != "${EXPECTED_DEPLOYER,,}" ]]; then
  printf '%s\n' 'Refusing deployment: signer does not match EXPECTED_DEPLOYER.' >&2
  exit 1
fi

source_commit="${SOURCE_COMMIT:-$(git -C "$repository_root" rev-parse HEAD)}"

(
  cd "$repository_root/contracts"
  forge script script/DeployCertificateRegistry.s.sol \
    --rpc-url "$AMOY_RPC_URL" \
    --broadcast
  node scripts/export-artifacts.mjs \
    --network=amoy \
    --chain-id=80002 \
    --source-commit="$source_commit"
)

registry_address="$(
  node -e 'const manifest=require(process.argv[1]); process.stdout.write(manifest.certificateRegistry)' \
    "$repository_root/contracts/deployments/amoy.json"
)"
constructor_arguments="$(cast abi-encode 'constructor(address)' "$CONTRACT_ADMIN")"

(
  cd "$repository_root/contracts"
  forge verify-contract \
    "$registry_address" \
    src/CertificateRegistry.sol:CertificateRegistry \
    --chain 80002 \
    --compiler-version 0.8.30 \
    --constructor-args "$constructor_arguments" \
    --etherscan-api-key "$POLYGONSCAN_API_KEY" \
    --watch
  node scripts/record-explorer-evidence.mjs \
    --network=amoy \
    --chain-id=80002 \
    --address="$registry_address" \
    --explorer-base-url=https://amoy.polygonscan.com \
    --source-commit="$source_commit"
)

printf 'Amoy release verified: https://amoy.polygonscan.com/address/%s#code\n' \
  "$registry_address"
