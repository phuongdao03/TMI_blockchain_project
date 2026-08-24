#!/bin/bash
set -euo pipefail

required() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required environment variable: %s\n' "$name" >&2
    exit 1
  fi
}

for command_name in cast node; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command is unavailable: %s\n' "$command_name" >&2
    exit 1
  }
done

for variable_name in \
  BLOCKCHAIN_RPC_URL \
  CERTIFICATE_CONTRACT_ADDRESS \
  BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES \
  BLOCKCHAIN_ACTIVE_SIGNER_WALLET \
  CONTRACT_ADMIN \
  ISSUER_ADDRESS \
  EXPECTED_RUNTIME_BYTECODE_SHA256 \
  MINIMUM_SIGNER_BALANCE_WEI; do
  required "$variable_name"
done

if [[ ! "$BLOCKCHAIN_RPC_URL" =~ ^https:// ]]; then
  printf '%s\n' 'Production RPC must use HTTPS.' >&2
  exit 1
fi

chain_id="$(cast chain-id --rpc-url "$BLOCKCHAIN_RPC_URL")"
if [[ "$chain_id" != "137" ]]; then
  printf 'Refusing preflight: expected Polygon chain 137, received %s.\n' \
    "$chain_id" >&2
  exit 1
fi

allowed=false
IFS=',' read -r -a allowlist <<<"$BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES"
for candidate in "${allowlist[@]}"; do
  if [[ "${candidate,,}" == "${CERTIFICATE_CONTRACT_ADDRESS,,}" ]]; then
    allowed=true
  fi
done
if [[ "$allowed" != "true" ]]; then
  printf '%s\n' 'Certificate contract is not in the production allowlist.' >&2
  exit 1
fi

if [[ "${BLOCKCHAIN_ACTIVE_SIGNER_WALLET,,}" != "${ISSUER_ADDRESS,,}" ]]; then
  printf '%s\n' 'Active Super Admin wallet must be the contract issuer.' >&2
  exit 1
fi

balance_wei="$(
  cast balance --wei "$BLOCKCHAIN_ACTIVE_SIGNER_WALLET" \
    --rpc-url "$BLOCKCHAIN_RPC_URL"
)"
if ! awk -v actual="$balance_wei" -v minimum="$MINIMUM_SIGNER_BALANCE_WEI" \
  'BEGIN { exit !(actual + 0 >= minimum + 0) }'; then
  printf '%s\n' 'Active Super Admin signer balance is below the approved minimum.' >&2
  exit 1
fi

runtime_code="$(
  cast code "$CERTIFICATE_CONTRACT_ADDRESS" --rpc-url "$BLOCKCHAIN_RPC_URL"
)"
if [[ "$runtime_code" == "0x" ]]; then
  printf '%s\n' 'Certificate contract has no deployed runtime bytecode.' >&2
  exit 1
fi
runtime_bytecode_sha256="$(
  node -e 'const {createHash}=require("node:crypto"); const value=process.argv[1].replace(/^0x/, ""); process.stdout.write(`0x${createHash("sha256").update(Buffer.from(value, "hex")).digest("hex")}`)' \
    "$runtime_code"
)"
if [[ "${runtime_bytecode_sha256,,}" != "${EXPECTED_RUNTIME_BYTECODE_SHA256,,}" ]]; then
  printf '%s\n' 'Deployed runtime bytecode hash does not match the reviewed release.' >&2
  exit 1
fi

admin_role="0x$(printf '0%.0s' {1..64})"
pauser_role="$(cast keccak 'PAUSER_ROLE')"
issuer_role="$(cast keccak 'ISSUER_ROLE')"
for role_check in \
  "$admin_role:$CONTRACT_ADMIN:administrator" \
  "$pauser_role:$CONTRACT_ADMIN:pauser" \
  "$issuer_role:$ISSUER_ADDRESS:issuer"; do
  IFS=':' read -r role account label <<<"$role_check"
  has_role="$(
    cast call "$CERTIFICATE_CONTRACT_ADDRESS" \
      'hasRole(bytes32,address)(bool)' "$role" "$account" \
      --rpc-url "$BLOCKCHAIN_RPC_URL"
  )"
  if [[ "$has_role" != "true" ]]; then
    printf 'Required %s role is missing.\n' "$label" >&2
    exit 1
  fi
done

printf '%s\n' 'Polygon preflight passed without broadcasting a transaction.'
