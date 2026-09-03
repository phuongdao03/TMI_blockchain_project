#!/bin/bash
set -euo pipefail

# Read-only Polygon gate for the approved THVProofRegistry. It never signs,
# broadcasts, deploys, grants, or revokes a role.
readonly APPROVED_REGISTRY="0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F"
readonly APPROVED_ADMIN="0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe"
readonly APPROVED_VERIFIER="0xBfA38182f0D24589e7898DD4892C58c3FDa58042"

required() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required environment variable: %s\n' "$name" >&2
    exit 1
  fi
}

command -v cast >/dev/null 2>&1 || {
  printf '%s\n' 'Required command is unavailable: cast' >&2
  exit 1
}

for variable_name in \
  BLOCKCHAIN_RPC_URL \
  THV_PROOF_REGISTRY_CONTRACT_ADDRESS \
  BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES \
  ADMIN_WALLET_ADDRESS \
  SIGNER_WALLET_ADDRESS \
  MINIMUM_SIGNER_BALANCE_WEI; do
  required "$variable_name"
done

if [[ ! "$BLOCKCHAIN_RPC_URL" =~ ^https:// ]]; then
  printf '%s\n' 'Production RPC must use HTTPS.' >&2
  exit 1
fi
if [[ "${THV_PROOF_REGISTRY_CONTRACT_ADDRESS,,}" != "${APPROVED_REGISTRY,,}" ]]; then
  printf '%s\n' 'THV registry is not the approved Polygon deployment.' >&2
  exit 1
fi
if [[ "${ADMIN_WALLET_ADDRESS,,}" != "${APPROVED_ADMIN,,}" ]] || \
   [[ "${SIGNER_WALLET_ADDRESS,,}" != "${APPROVED_VERIFIER,,}" ]]; then
  printf '%s\n' 'THV role holders do not match the approved identities.' >&2
  exit 1
fi

chain_id="$(cast chain-id --rpc-url "$BLOCKCHAIN_RPC_URL")"
if [[ "$chain_id" != "137" ]]; then
  printf 'Refusing preflight: expected Polygon chain 137, received %s.\n' \
    "$chain_id" >&2
  exit 1
fi

IFS=',' read -r -a allowlist <<<"$BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES"
if [[ "${#allowlist[@]}" -ne 1 ]] || \
   [[ "${allowlist[0],,}" != "${APPROVED_REGISTRY,,}" ]]; then
  printf '%s\n' 'Production allowlist must contain only the approved THV registry.' >&2
  exit 1
fi

runtime_code="$(cast code "$APPROVED_REGISTRY" --rpc-url "$BLOCKCHAIN_RPC_URL")"
if [[ "$runtime_code" == "0x" ]]; then
  printf '%s\n' 'THV registry has no deployed runtime bytecode.' >&2
  exit 1
fi

admin_role="0x$(printf '0%.0s' {1..64})"
verifier_role="$(cast keccak 'VERIFIER_ROLE')"
for role_check in \
  "$admin_role:$APPROVED_ADMIN:administrator" \
  "$verifier_role:$APPROVED_VERIFIER:verifier"; do
  IFS=':' read -r role account label <<<"$role_check"
  has_role="$(cast call "$APPROVED_REGISTRY" \
    'hasRole(bytes32,address)(bool)' "$role" "$account" \
    --rpc-url "$BLOCKCHAIN_RPC_URL")"
  if [[ "$has_role" != "true" ]]; then
    printf 'Required %s role is missing.\n' "$label" >&2
    exit 1
  fi
done

admin_has_verifier="$(cast call "$APPROVED_REGISTRY" \
  'hasRole(bytes32,address)(bool)' "$verifier_role" "$APPROVED_ADMIN" \
  --rpc-url "$BLOCKCHAIN_RPC_URL")"
verifier_has_admin="$(cast call "$APPROVED_REGISTRY" \
  'hasRole(bytes32,address)(bool)' "$admin_role" "$APPROVED_VERIFIER" \
  --rpc-url "$BLOCKCHAIN_RPC_URL")"
if [[ "$admin_has_verifier" != "false" ]] || [[ "$verifier_has_admin" != "false" ]]; then
  printf '%s\n' 'THV administrator and verifier roles must remain separated.' >&2
  exit 1
fi

balance_wei="$(cast balance --wei "$APPROVED_VERIFIER" --rpc-url "$BLOCKCHAIN_RPC_URL")"
if ! awk -v actual="$balance_wei" -v minimum="$MINIMUM_SIGNER_BALANCE_WEI" \
  'BEGIN { exit !(actual + 0 >= minimum + 0) }'; then
  printf '%s\n' 'Approved verifier balance is below the operational minimum.' >&2
  exit 1
fi

printf '%s\n' 'THVProofRegistry Polygon preflight passed without broadcasting.'
