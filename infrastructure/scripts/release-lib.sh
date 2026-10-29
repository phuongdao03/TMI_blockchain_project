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

require_encryption_key() {
  local env_file="$1"
  local key_name="$2"
  local encoded_key decoded_size
  encoded_key="$(read_env_value "$env_file" "$key_name")"
  if [[ -z "$encoded_key" ]] || ! printf '%s' "$encoded_key" | base64 --decode >/dev/null 2>&1; then
    release_error "$key_name must be valid base64 encoding of 32 bytes"
    return 65
  fi
  decoded_size="$(printf '%s' "$encoded_key" | base64 --decode 2>/dev/null | wc -c)"
  if [[ "$decoded_size" -ne 32 ]]; then
    release_error "$key_name must decode to exactly 32 bytes"
    return 65
  fi
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
  require_command base64 || return $?
  require_encryption_key "$env_file" "PII_ENCRYPTION_KEY" || return $?
  require_encryption_key "$env_file" "AUTH_OUTBOX_ENCRYPTION_KEY" || return $?
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

collect_release_diagnostics() {
  release_error "Collecting failed release diagnostics before rollback"
  compose_command ps -a >&2 || true
  compose_command logs --no-color --tail 100 backend >&2 || true
  compose_command exec -T backend python -c '
import urllib.request, urllib.error
try:
    response = urllib.request.urlopen("http://127.0.0.1:8000/ready", timeout=10)
    print("Backend readiness:", response.read().decode())
except urllib.error.HTTPError as error:
    print("Backend readiness:", error.code, error.read().decode())
except Exception as error:
    print("Backend readiness unavailable:", type(error).__name__, str(error))
' >&2 || true
}

wait_for_release() {
  compose_command up -d --remove-orphans --wait --wait-timeout "$DEPLOY_HEALTH_TIMEOUT_SECONDS" || return $?
  verify_public_health
}
