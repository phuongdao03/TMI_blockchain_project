#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: collect-database-readiness.sh <evidence-directory>" >&2
  exit 64
fi

if [[ -z "${DATABASE_DIRECT_URL:-}" ]]; then
  echo "DATABASE_DIRECT_URL is required" >&2
  exit 64
fi

case "$DATABASE_DIRECT_URL" in
  postgresql://*|postgres://*) database_url="$DATABASE_DIRECT_URL" ;;
  postgresql+asyncpg://*) database_url="postgresql://${DATABASE_DIRECT_URL#postgresql+asyncpg://}" ;;
  *)
    echo "DATABASE_DIRECT_URL must use PostgreSQL" >&2
    exit 64
    ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
query_file="$project_root/infrastructure/database/critical-query-plans.sql"
evidence_dir="$1"

umask 077
mkdir -p "$evidence_dir"

PGCONNECT_TIMEOUT=10 psql "$database_url" \
  --no-psqlrc \
  --set ON_ERROR_STOP=1 \
  --file "$query_file" \
  > "$evidence_dir/query-plans.txt"

PGCONNECT_TIMEOUT=10 psql "$database_url" \
  --no-psqlrc \
  --set ON_ERROR_STOP=1 \
  --tuples-only \
  --no-align \
  --command "SELECT json_build_object(
    'captured_at', clock_timestamp(),
    'server_version', current_setting('server_version'),
    'database_size_bytes', pg_database_size(current_database()),
    'migration_revision', (SELECT version_num FROM alembic_version LIMIT 1)
  );" \
  > "$evidence_dir/database-summary.json"

(
  cd "$evidence_dir"
  sha256sum query-plans.txt database-summary.json > manifest.sha256
)

echo "database readiness evidence written with restricted permissions" >&2
