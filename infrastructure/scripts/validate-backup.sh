#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: validate-backup.sh <backup-directory>" >&2
  exit 64
fi

backup_dir="$1"
if [[ ! -d "$backup_dir" ]]; then
  echo "backup directory not found" >&2
  exit 66
fi

for required in manifest.sha256 certificate-metadata.json cloudinary-inventory.json contract-artifacts.tar.gz; do
  if [[ ! -s "$backup_dir/$required" ]]; then
    echo "missing or empty backup artifact: $required" >&2
    exit 65
  fi
done

declare -A expected=()
declare -A seen=()
for required in certificate-metadata.json cloudinary-inventory.json contract-artifacts.tar.gz; do
  expected["$required"]=1
done

while read -r digest artifact extra; do
  [[ -z "${digest:-}" ]] && continue
  if [[ -n "${extra:-}" || ! "$digest" =~ ^[[:xdigit:]]{64}$ ]]; then
    echo "invalid checksum manifest entry" >&2
    exit 65
  fi
  artifact="${artifact#\*}"
  if [[ -z "${artifact:-}" || -z "${expected[$artifact]+x}" ]]; then
    echo "checksum manifest references an unexpected artifact" >&2
    exit 65
  fi
  if [[ -n "${seen[$artifact]+x}" ]]; then
    echo "checksum manifest contains a duplicate artifact" >&2
    exit 65
  fi
  seen["$artifact"]=1
done < "$backup_dir/manifest.sha256"

for required in "${!expected[@]}"; do
  if [[ -z "${seen[$required]+x}" ]]; then
    echo "checksum manifest is missing artifact: $required" >&2
    exit 65
  fi
done

(
  cd "$backup_dir"
  sha256sum --check --status manifest.sha256
)

python - "$backup_dir/certificate-metadata.json" "$backup_dir/cloudinary-inventory.json" <<'PY'
import json
import sys

for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"backup metadata must be a JSON object: {path}")
PY

archive_listing="$(tar -tzf "$backup_dir/contract-artifacts.tar.gz")"
if [[ -z "$archive_listing" ]]; then
  echo "contract artifact archive is empty" >&2
  exit 65
fi
while IFS= read -r member; do
  case "$member" in
    /*|../*|*/../*|..)
      echo "contract artifact archive contains an unsafe path" >&2
      exit 65
      ;;
  esac
done <<< "$archive_listing"

echo '{"status":"valid","artifacts":4}'
