#!/bin/bash
set -e

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
cd "$project_root"

docker compose --profile frontend up -d --build --wait --wait-timeout 240
mkdir -p .runtime
runtime_file=.runtime/local-contract.env
contract_address=""
if [ -f "$runtime_file" ]; then
  contract_address="$(sed -n 's/^CERTIFICATE_CONTRACT_ADDRESS=//p' "$runtime_file" | head -n 1)"
fi

contract_code="0x"
if printf '%s' "$contract_address" | grep -Eq '^0x[0-9a-fA-F]{40}$'; then
  contract_code="$(curl --fail --silent --show-error \
    --header 'Content-Type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getCode\",\"params\":[\"$contract_address\",\"latest\"],\"id\":1}" \
    http://localhost:8545 | sed -n 's/.*"result":"\([^"]*\)".*/\1/p')"
fi

if [ "$contract_code" = "0x" ] || [ -z "$contract_code" ]; then
  docker compose --profile tools run --rm contract-deps
  docker compose --profile tools run --rm contract-deployer
  contract_address="$(docker compose --profile tools run --rm --no-deps contract-deps \
    node -e "const f=require('/contracts/broadcast/DeployCertificateRegistry.s.sol/31337/run-latest.json'); console.log(f.receipts.filter(x=>x.contractAddress).at(-1).contractAddress)")"
fi

{
  printf '%s\n' '# Generated local-only runtime values. This file is gitignored.'
  printf 'CERTIFICATE_CONTRACT_ADDRESS=%s\n' "$contract_address"
  printf 'BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES=%s\n' "$contract_address"
} > "$runtime_file"

docker compose --profile frontend up -d --force-recreate --wait --wait-timeout 180 \
  backend worker scheduler frontend nginx
printf 'Local bootstrap complete. Contract: %s\n' "$contract_address"
printf '%s\n' 'No application accounts were created. Provision a local Super Admin explicitly when needed.'
