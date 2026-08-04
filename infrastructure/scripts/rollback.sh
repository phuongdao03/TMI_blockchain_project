#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: rollback.sh <previous-immutable-image-tag>" >&2
  exit 64
fi

previous_tag="$1"
case "$previous_tag" in
  *[!A-Za-z0-9._-]*|'')
    echo "invalid image tag" >&2
    exit 64
    ;;
esac

export IMAGE_TAG="$previous_tag"
compose_file="infrastructure/compose.production.yaml"

docker compose --env-file infrastructure/.env.production -f "$compose_file" pull
docker compose --env-file infrastructure/.env.production -f "$compose_file" up -d --remove-orphans
docker compose --env-file infrastructure/.env.production -f "$compose_file" ps

echo "Application images rolled back. Database downgrade is intentionally manual." >&2
