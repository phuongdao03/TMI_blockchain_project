#!/bin/bash
set -euo pipefail

required() {
  local variable_name="$1"
  if [[ -z "${!variable_name:-}" ]]; then
    printf 'Missing required environment variable: %s\n' "$variable_name" >&2
    exit 1
  fi
}

for variable_name in PAYOS_CLIENT_ID PAYOS_API_KEY PAYOS_WEBHOOK_URL; do
  required "$variable_name"
done

readonly payos_base_url="${PAYOS_BASE_URL:-https://api-merchant.payos.vn}"
if [[ ! "$payos_base_url" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]]; then
  printf '%s\n' 'PAYOS_BASE_URL must be an HTTPS origin without a path.' >&2
  exit 1
fi
if [[ ! "$PAYOS_WEBHOOK_URL" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?/api/v1/webhooks/payments/payos$ ]]; then
  printf '%s\n' 'PAYOS_WEBHOOK_URL must be the public HTTPS PayOS callback URL.' >&2
  exit 1
fi

command -v curl >/dev/null 2>&1 || {
  printf '%s\n' 'Required command is unavailable: curl' >&2
  exit 1
}

response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

# Read credentials through curl config on stdin so they do not appear in the
# process command line or shell history.
{
  printf 'url = "%s/confirm-webhook"\n' "$payos_base_url"
  printf 'header = "Content-Type: application/json"\n'
  printf 'header = "x-client-id: %s"\n' "$PAYOS_CLIENT_ID"
  printf 'header = "x-api-key: %s"\n' "$PAYOS_API_KEY"
  printf 'data = "{\\"webhookUrl\\":\\"%s\\"}"\n' "$PAYOS_WEBHOOK_URL"
} | curl \
  --silent \
  --show-error \
  --fail \
  --request POST \
  --config - \
  --output "$response_file"

if ! grep -Eq '"code"[[:space:]]*:[[:space:]]*"00"' "$response_file"; then
  printf '%s\n' 'PayOS did not confirm the webhook URL.' >&2
  exit 1
fi

printf '{"status":"configured","webhookUrl":"%s"}\n' "$PAYOS_WEBHOOK_URL"
