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

(
  cd "$backup_dir"
  sha256sum --check manifest.sha256
)

python -m json.tool "$backup_dir/certificate-metadata.json" >/dev/null
python -m json.tool "$backup_dir/cloudinary-inventory.json" >/dev/null
tar -tzf "$backup_dir/contract-artifacts.tar.gz" >/dev/null

echo '{"status":"valid","artifacts":3}'
