#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: deploy.sh <immutable-image-tag>" >&2
  exit 64
fi

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/release-lib.sh"

release_tag="$1"
validate_release_tag "$release_tag"
require_command docker
require_command curl
require_command flock

project_root="$(release_root)"
PRODUCTION_ENV_FILE="${PRODUCTION_ENV_FILE:-$project_root/infrastructure/.env.production}"
PRODUCTION_COMPOSE_FILE="$project_root/infrastructure/compose.production.yaml"
EDGE_PROXY_MODE="${EDGE_PROXY_MODE:-$(read_env_value "$PRODUCTION_ENV_FILE" "EDGE_PROXY_MODE")}"
EDGE_PROXY_MODE="${EDGE_PROXY_MODE:-container-nginx}"
case "$EDGE_PROXY_MODE" in
  host-nginx)
    PRODUCTION_COMPOSE_OVERRIDE_FILE="$project_root/infrastructure/compose.host-nginx.yaml"
    ;;
  container-nginx) ;;
  *)
    release_error "unsupported EDGE_PROXY_MODE: $EDGE_PROXY_MODE"
    exit 65
    ;;
esac
if [[ -z "${DEPLOY_HEALTH_TIMEOUT_SECONDS:-}" ]]; then
  DEPLOY_HEALTH_TIMEOUT_SECONDS="$(read_env_value "$PRODUCTION_ENV_FILE" "DEPLOY_HEALTH_TIMEOUT_SECONDS")"
fi
DEPLOY_HEALTH_TIMEOUT_SECONDS="${DEPLOY_HEALTH_TIMEOUT_SECONDS:-180}"
if [[ -z "${AUTO_ROLLBACK_ON_FAILURE:-}" ]]; then
  AUTO_ROLLBACK_ON_FAILURE="$(read_env_value "$PRODUCTION_ENV_FILE" "AUTO_ROLLBACK_ON_FAILURE")"
fi
AUTO_ROLLBACK_ON_FAILURE="${AUTO_ROLLBACK_ON_FAILURE:-true}"
release_dir="$project_root/.releases"
current_tag_file="$release_dir/current-image-tag"
previous_tag_file="$release_dir/previous-image-tag"
lock_file="$release_dir/deploy.lock"

require_production_environment "$PRODUCTION_ENV_FILE"
if [[ "$(read_env_value "$PRODUCTION_ENV_FILE" "RELEASE_MODE")" == "preview" ]]; then
  bash "$project_root/infrastructure/scripts/validate-preview-environment.sh" \
    "$PRODUCTION_ENV_FILE"
fi
mkdir -p "$release_dir"
chmod 700 "$release_dir"
touch "$lock_file"

exec 9>"$lock_file"
flock -n 9 || {
  release_error "another deployment or rollback is already running"
  exit 75
}

export IMAGE_TAG="$release_tag"
compose_command config -q
previous_tag="$(cat "$current_tag_file" 2>/dev/null || true)"

deploy_release() {
  compose_command pull || return 1
  compose_command run --rm backend alembic upgrade head || return 1
  wait_for_release || return 1
}

if ! deploy_release; then
  release_error "release $release_tag failed health validation"
  if [[ "$AUTO_ROLLBACK_ON_FAILURE" == "true" && -n "$previous_tag" && "$previous_tag" != "$release_tag" ]]; then
    release_error "restoring previous application images: $previous_tag"
    export IMAGE_TAG="$previous_tag"
    compose_command pull
    wait_for_release
  fi
  exit 70
fi

if [[ -n "$previous_tag" && "$previous_tag" != "$release_tag" ]]; then
  write_release_tag "$previous_tag_file" "$previous_tag"
fi
write_release_tag "$current_tag_file" "$release_tag"
compose_command ps
