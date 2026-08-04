#!/bin/bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
  echo "usage: rollback.sh [previous-immutable-image-tag]" >&2
  exit 64
fi

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/release-lib.sh"

require_command docker
require_command curl
require_command flock

project_root="$(release_root)"
PRODUCTION_ENV_FILE="${PRODUCTION_ENV_FILE:-$project_root/infrastructure/.env.production}"
PRODUCTION_COMPOSE_FILE="$project_root/infrastructure/compose.production.yaml"
if [[ -z "${DEPLOY_HEALTH_TIMEOUT_SECONDS:-}" ]]; then
  DEPLOY_HEALTH_TIMEOUT_SECONDS="$(read_env_value "$PRODUCTION_ENV_FILE" "DEPLOY_HEALTH_TIMEOUT_SECONDS")"
fi
DEPLOY_HEALTH_TIMEOUT_SECONDS="${DEPLOY_HEALTH_TIMEOUT_SECONDS:-180}"
release_dir="$project_root/.releases"
current_tag_file="$release_dir/current-image-tag"
previous_tag_file="$release_dir/previous-image-tag"
lock_file="$release_dir/deploy.lock"

require_production_environment "$PRODUCTION_ENV_FILE"
mkdir -p "$release_dir"
chmod 700 "$release_dir"
touch "$lock_file"

exec 9>"$lock_file"
flock -n 9 || {
  release_error "another deployment or rollback is already running"
  exit 75
}

previous_tag="${1:-$(cat "$previous_tag_file" 2>/dev/null || true)}"
validate_release_tag "$previous_tag"
compose_command config -q

current_tag="$(cat "$current_tag_file" 2>/dev/null || true)"
export IMAGE_TAG="$previous_tag"
compose_command pull
wait_for_release

if [[ -n "$current_tag" && "$current_tag" != "$previous_tag" ]]; then
  write_release_tag "$previous_tag_file" "$current_tag"
fi
write_release_tag "$current_tag_file" "$previous_tag"
compose_command ps

echo "Application images rolled back. Database downgrade is intentionally manual." >&2
