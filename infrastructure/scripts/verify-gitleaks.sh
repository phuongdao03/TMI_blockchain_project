#!/usr/bin/env bash
set -euo pipefail

readonly scanner_image="ghcr.io/gitleaks/gitleaks:v8.30.1"
readonly repository_root="$(git rev-parse --show-toplevel)"
readonly fixture_directory="$(mktemp -d)"
readonly snapshot_directory="$(mktemp -d)"

docker_host_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

readonly repository_mount="$(docker_host_path "${repository_root}")"
readonly config_mount="$(docker_host_path "${repository_root}/.gitleaks.toml")"
readonly fixture_mount="$(docker_host_path "${fixture_directory}")"
readonly snapshot_mount="$(docker_host_path "${snapshot_directory}")"

cleanup() {
  rm -rf -- "${fixture_directory}"
  rm -rf -- "${snapshot_directory}"
}
trap cleanup EXIT

existing_worktree_files() {
  while IFS= read -r -d '' path; do
    if [[ -f "${repository_root}/${path}" ]]; then
      printf '%s\0' "${path}"
    fi
  done < <(
    git -C "${repository_root}" ls-files --cached --others --exclude-standard -z
  )
}

existing_worktree_files \
  | tar --null --files-from=- --create --file=- \
  | tar --extract --file=- --directory="${snapshot_directory}"

MSYS_NO_PATHCONV=1 docker run --rm \
  --volume "${repository_mount}:/repo:ro" \
  --workdir /repo \
  "${scanner_image}" git \
  --config /repo/.gitleaks.toml \
  --redact \
  --no-banner \
  /repo

MSYS_NO_PATHCONV=1 docker run --rm \
  --volume "${config_mount}:/config/.gitleaks.toml:ro" \
  --volume "${snapshot_mount}:/snapshot:ro" \
  "${scanner_image}" dir \
  --config /config/.gitleaks.toml \
  --redact \
  --no-banner \
  /snapshot

# Build a synthetic canary only at runtime so no secret-like value is committed.
printf '"client_%s": "%s%s"\n' \
  "secret" \
  "synthetic-canary-not-real-" \
  "0123456789abcdef" >"${fixture_directory}/canary.json"

set +e
MSYS_NO_PATHCONV=1 docker run --rm \
  --volume "${config_mount}:/config/.gitleaks.toml:ro" \
  --volume "${fixture_mount}:/fixture:ro" \
  "${scanner_image}" dir \
  --config /config/.gitleaks.toml \
  --redact \
  --no-banner \
  /fixture
readonly canary_status=$?
set -e

if [[ "${canary_status}" -ne 1 ]]; then
  printf '%s\n' '{"status":"error","check":"gitleaks-synthetic-canary"}' >&2
  exit 1
fi

printf '%s\n' '{"status":"ok","check":"gitleaks-history-worktree-canary"}'
