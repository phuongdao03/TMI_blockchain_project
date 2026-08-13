#!/bin/bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"

cleanup() {
  docker compose stop anvil >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose up -d --wait anvil
docker compose run --rm --no-deps contract-deployer

source_commit="${SOURCE_COMMIT:-$(git rev-parse HEAD)}"
node contracts/scripts/export-artifacts.mjs \
  --network=local \
  --chain-id=31337 \
  --source-commit="$source_commit"

registry_address="$(
  node -e 'const manifest=require("./contracts/deployments/local.json"); process.stdout.write(manifest.certificateRegistry)'
)"
local_private_key="$(docker compose logs --no-color anvil \
  | sed -n 's/.*(0) \(0x[0-9a-fA-F]\{64\}\).*/\1/p' | head -n 1)"
if ! printf '%s' "$local_private_key" | grep -Eq '^0x[0-9a-fA-F]{64}$'; then
  printf '%s\n' 'Could not read the ephemeral Anvil signer key.' >&2
  exit 1
fi
certificate_id="0x1111111111111111111111111111111111111111111111111111111111111111"
dossier_hash="0x2222222222222222222222222222222222222222222222222222222222222222"
metadata_hash="0x3333333333333333333333333333333333333333333333333333333333333333"
reason_hash="0x4444444444444444444444444444444444444444444444444444444444444444"
document_evidence_key="0x5555555555555555555555555555555555555555555555555555555555555555"
document_commitment="0x6666666666666666666666666666666666666666666666666666666666666666"
modified_document_commitment="0x7777777777777777777777777777777777777777777777777777777777777777"
empty_evidence_key="0x0000000000000000000000000000000000000000000000000000000000000000"

cast_command=(docker compose run --rm --no-deps --entrypoint cast contract-deployer)

"${cast_command[@]}" send --rpc-url http://anvil:8545 \
  --private-key "$local_private_key" "$registry_address" \
  "issueCertificate(bytes32,bytes32,bytes32,uint64,uint64)" \
  "$certificate_id" "$dossier_hash" "$metadata_hash" 100 200 >/dev/null

issued_record="$(
  "${cast_command[@]}" call --rpc-url http://anvil:8545 "$registry_address" \
    "getCertificate(bytes32)((bytes32,bytes32,bytes32,uint64,uint64,uint32,bool))" \
    "$certificate_id"
)"
grep -q "false" <<<"$issued_record"

"${cast_command[@]}" send --rpc-url http://anvil:8545 \
  --private-key "$local_private_key" "$registry_address" \
  "anchorDocumentEvidence(bytes32,bytes32,bytes32,uint32,uint64)" \
  "$document_evidence_key" "$document_commitment" "$empty_evidence_key" 1 300 >/dev/null

document_record="$(
  "${cast_command[@]}" call --rpc-url http://anvil:8545 "$registry_address" \
    "getDocumentEvidence(bytes32)((bytes32,bytes32,uint64,uint32))" \
    "$document_evidence_key"
)"
grep -qi "$document_commitment" <<<"$document_record"

matching_document="$(
  "${cast_command[@]}" call --rpc-url http://anvil:8545 "$registry_address" \
    "verifyDocumentEvidence(bytes32,bytes32)(bool)" \
    "$document_evidence_key" "$document_commitment"
)"
grep -q "true" <<<"$matching_document"

modified_document="$(
  "${cast_command[@]}" call --rpc-url http://anvil:8545 "$registry_address" \
    "verifyDocumentEvidence(bytes32,bytes32)(bool)" \
    "$document_evidence_key" "$modified_document_commitment"
)"
grep -q "false" <<<"$modified_document"

"${cast_command[@]}" send --rpc-url http://anvil:8545 \
  --private-key "$local_private_key" "$registry_address" \
  "revokeCertificate(bytes32,bytes32)" "$certificate_id" "$reason_hash" >/dev/null

revoked_record="$(
  "${cast_command[@]}" call --rpc-url http://anvil:8545 "$registry_address" \
    "getCertificate(bytes32)((bytes32,bytes32,bytes32,uint64,uint64,uint32,bool))" \
    "$certificate_id"
)"
grep -q "true" <<<"$revoked_record"

printf '%s\n' "Anvil certificate and document evidence smoke passed."
