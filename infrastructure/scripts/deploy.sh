#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: deploy.sh <immutable-image-tag>" >&2
  exit 64
fi

release_tag="$1"
case "$release_tag" in
  *[!A-Za-z0-9._-]*|'')
    echo "invalid image tag" >&2
    exit 64
    ;;
esac

export IMAGE_TAG="$release_tag"
compose_file="infrastructure/compose.production.yaml"

docker compose --env-file infrastructure/.env.production -f "$compose_file" pull
docker compose --env-file infrastructure/.env.production -f "$compose_file" run --rm backend alembic upgrade head
docker compose --env-file infrastructure/.env.production -f "$compose_file" up -d --remove-orphans
docker compose --env-file infrastructure/.env.production -f "$compose_file" ps
