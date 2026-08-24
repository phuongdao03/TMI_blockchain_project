#!/bin/bash

release_error() {
  echo "$*" >&2
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    release_error "required command is unavailable: $1"
    return 69
  }
}

validate_release_tag() {
  local release_tag="$1"
  case "$release_tag" in
    *[!A-Za-z0-9._-]* | "")
      release_error "invalid image tag"
      return 64
      ;;
  esac
}

release_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$script_dir/../.." && pwd
}

read_env_value() {
  local env_file="$1"
  local key="$2"
  awk -F= -v key="$key" \
    '$1 == key { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit }' \
    "$env_file"
}

require_production_environment() {
  local env_file="$1"
  [[ -f "$env_file" ]] || {
    release_error "production environment file is missing: $env_file"
    return 66
  }

  local mode
  mode="$(stat -c '%a' "$env_file")"
  if (( 8#$mode & 8#077 )); then
    release_error "production environment file must be owner-readable only (0600): $env_file"
    return 77
  fi

  if grep -Eq '=(replace|replace-with-release-sha)([[:space:]]*)$' "$env_file"; then
    release_error "production environment still contains placeholder values"
    return 65
  fi
}

compose_command() {
  local release_mode
  local -a compose_arguments
  release_mode="$(read_env_value "$PRODUCTION_ENV_FILE" "RELEASE_MODE")"
  release_mode="${release_mode:-full}"
  compose_arguments=(
    docker compose
    --env-file "$PRODUCTION_ENV_FILE"
    -f "$PRODUCTION_COMPOSE_FILE"
  )
  if [[ "$release_mode" == "full" ]]; then
    compose_arguments+=(--profile full)
  fi
  if [[ -n "${PRODUCTION_COMPOSE_OVERRIDE_FILE:-}" ]]; then
    compose_arguments+=(-f "$PRODUCTION_COMPOSE_OVERRIDE_FILE")
  fi
  "${compose_arguments[@]}" "$@"
}

verify_public_health() {
  local app_domain
  app_domain="$(read_env_value "$PRODUCTION_ENV_FILE" "APP_DOMAIN")"
  [[ -n "$app_domain" ]] || {
    release_error "APP_DOMAIN is required for the deployment health check"
    return 65
  }

  curl --fail --silent --show-error --max-time 15 --retry 3 --retry-delay 2 \
    --resolve "${app_domain}:443:127.0.0.1" \
    "https://${app_domain}/health" >/dev/null
}

write_release_tag() {
  local destination="$1"
  local release_tag="$2"
  local temporary_file
  temporary_file="${destination}.tmp"
  printf '%s\n' "$release_tag" >"$temporary_file"
  mv "$temporary_file" "$destination"
}

wait_for_release() {
  compose_command up -d --remove-orphans --wait --wait-timeout "$DEPLOY_HEALTH_TIMEOUT_SECONDS"
  verify_public_health
}
