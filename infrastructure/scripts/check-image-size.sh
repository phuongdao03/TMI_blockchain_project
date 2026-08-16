#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: check-image-size.sh <image> <maximum-megabytes>" >&2
  exit 64
fi

image="$1"
maximum_megabytes="$2"
if [[ ! "$maximum_megabytes" =~ ^[1-9][0-9]*$ ]]; then
  echo "maximum-megabytes must be a positive integer" >&2
  exit 64
fi

size_bytes="$(docker image inspect "$image" --format '{{.Size}}')"
maximum_bytes=$((maximum_megabytes * 1024 * 1024))
size_megabytes=$(((size_bytes + 1024 * 1024 - 1) / 1024 / 1024))

printf '%s: %s MiB (budget %s MiB)\n' "$image" "$size_megabytes" "$maximum_megabytes"
if ((size_bytes > maximum_bytes)); then
  echo "image exceeds the approved size budget" >&2
  exit 1
fi
