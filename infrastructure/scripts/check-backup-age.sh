#!/bin/bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: check-backup-age.sh <backup-root> [max-age-hours]" >&2
  exit 64
fi

backup_root="$1"
max_age_hours="${2:-26}"
if [[ ! -d "$backup_root" ]]; then
  echo "backup root not found" >&2
  exit 66
fi
if [[ ! "$max_age_hours" =~ ^[0-9]+$ || "$max_age_hours" -eq 0 ]]; then
  echo "max-age-hours must be a positive integer" >&2
  exit 64
fi

newest_dir=""
newest_mtime=0
while IFS= read -r -d '' manifest; do
  candidate_dir="$(dirname "$manifest")"
  candidate_mtime="$(stat -c %Y "$manifest")"
  if (( candidate_mtime > newest_mtime )); then
    newest_mtime="$candidate_mtime"
    newest_dir="$candidate_dir"
  fi
done < <(find "$backup_root" -type f -name manifest.sha256 -print0)

if [[ -z "$newest_dir" ]]; then
  echo "no backup manifest found" >&2
  exit 65
fi

"$(dirname "$0")/validate-backup.sh" "$newest_dir" >/dev/null

now="$(date +%s)"
age_seconds=$((now - newest_mtime))
max_age_seconds=$((max_age_hours * 3600))
backup_name="$(basename "$newest_dir")"
if [[ ! "$backup_name" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "backup directory name contains unsupported characters" >&2
  exit 65
fi
if (( age_seconds > max_age_seconds )); then
  printf '{"status":"stale","backup":"%s","age_seconds":%d,"max_age_seconds":%d}\n' \
    "$backup_name" "$age_seconds" "$max_age_seconds"
  exit 70
fi

printf '{"status":"valid","backup":"%s","age_seconds":%d,"max_age_seconds":%d}\n' \
  "$backup_name" "$age_seconds" "$max_age_seconds"
