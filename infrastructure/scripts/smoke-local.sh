#!/bin/bash
set -e

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
cd "$project_root"

fail() {
  printf 'Smoke failure: %s\nRecovery: docker compose ps; docker compose logs %s\n' "$1" "$2" >&2
  exit 1
}

"$script_dir/bootstrap-local.sh"
curl --fail --silent --show-error http://localhost:3000 >/dev/null || fail frontend frontend
curl --fail --silent --show-error http://localhost:8000/ready >/dev/null || fail backend backend
curl --fail --silent --show-error http://localhost:8025/api/v1/info >/dev/null || fail Mailpit mailpit
curl --fail --silent --show-error http://localhost:9099/emulator/v1/projects/tmi-local/config >/dev/null || fail Firebase firebase-emulator

migration="$(docker compose exec -T postgres psql -U tmi_local -d tmi_local -tAc 'select version_num from alembic_version')" || fail PostgreSQL postgres
[ -n "$migration" ] || fail PostgreSQL migrate
[ "$(docker compose exec -T redis redis-cli ping)" = "PONG" ] || fail Redis redis
chain_id="$(curl --fail --silent --show-error --header 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
  http://localhost:8545 | sed -n 's/.*"result":"\([^"]*\)".*/\1/p')"
[ "$chain_id" = "0x7a69" ] || fail Anvil anvil

printf '%s\n' 'Local smoke passed: frontend, backend, PostgreSQL, Redis, Mailpit, Firebase and Anvil.'
