#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: validate-preview-environment.sh <environment-file>" >&2
  exit 64
fi

environment_file="$1"
[[ -f "$environment_file" ]] || {
  echo "preview environment file is missing" >&2
  exit 66
}

read_value() {
  awk -F= -v key="$1" \
    '$1 == key { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit }' \
    "$environment_file"
}

required_keys=(
  REGISTRY IMAGE_PREFIX APP_DOMAIN TLS_CERTIFICATE_DIR
  EDGE_PROXY_MODE FRONTEND_HOST_PORT BACKEND_HOST_PORT
  APP_ENV RELEASE_MODE APP_BASE_URL CORS_ALLOWED_ORIGINS
  DATABASE_URL DATABASE_DIRECT_URL REDIS_PASSWORD REDIS_URL
  JWT_SECRET AUTH_CSRF_SECRET AUTH_OUTBOX_ENCRYPTION_KEY
  PII_ENCRYPTION_KEY AUDIT_INTEGRITY_KEY FIREBASE_PROJECT_ID
  ENGAGEMENT_VISITOR_HMAC_SECRET PAYMENT_PROVIDER
)

for key in "${required_keys[@]}"; do
  [[ -n "$(read_value "$key")" ]] || {
    echo "required preview setting is missing: $key" >&2
    exit 65
  }
done

if grep -Eqi '(replace|inject-from-secret-manager|example\.com)' "$environment_file"; then
  echo "preview environment still contains placeholder values" >&2
  exit 65
fi

[[ "$(read_value APP_ENV)" == "production" ]] || {
  echo "preview APP_ENV must be production" >&2
  exit 65
}
[[ "$(read_value RELEASE_MODE)" == "preview" ]] || {
  echo "release mode must be preview" >&2
  exit 65
}
[[ "$(read_value EDGE_PROXY_MODE)" == "host-nginx" ]] || {
  echo "preview EDGE_PROXY_MODE must use the VPS host Nginx" >&2
  exit 65
}
[[ "$(read_value FRONTEND_HOST_PORT)" == "3100" ]] || {
  echo "preview FRONTEND_HOST_PORT must match the host Nginx upstream" >&2
  exit 65
}
[[ "$(read_value BACKEND_HOST_PORT)" == "8100" ]] || {
  echo "preview BACKEND_HOST_PORT must match the host Nginx upstream" >&2
  exit 65
}
[[ "$(read_value PAYMENT_PROVIDER)" == "disabled" ]] || {
  echo "PAYMENT_PROVIDER must be disabled for preview" >&2
  exit 65
}
[[ "$(read_value APP_BASE_URL)" == https://* ]] || {
  echo "preview APP_BASE_URL must use HTTPS" >&2
  exit 65
}
[[ "$(read_value CORS_ALLOWED_ORIGINS)" == https://* ]] || {
  echo "preview CORS origin must use HTTPS" >&2
  exit 65
}

app_domain="$(read_value APP_DOMAIN)"
[[ "$(read_value APP_BASE_URL)" == "https://$app_domain" ]] || {
  echo "APP_BASE_URL must match the HTTPS application domain" >&2
  exit 65
}
[[ "$(read_value CORS_ALLOWED_ORIGINS)" == "https://$app_domain" ]] || {
  echo "preview CORS origin must match the application domain" >&2
  exit 65
}
for key in DATABASE_URL DATABASE_DIRECT_URL; do
  database_url="$(read_value "$key")"
  if [[ "$database_url" != *"ssl=require"* && "$database_url" != *"sslmode=require"* ]]; then
    echo "$key must require TLS" >&2
    exit 65
  fi
done

certificate_root="$(read_value TLS_CERTIFICATE_DIR)/live/$app_domain"
for certificate_file in fullchain.pem privkey.pem; do
  [[ -r "$certificate_root/$certificate_file" ]] || {
    echo "TLS certificate file is unavailable: $certificate_file" >&2
    exit 66
  }
done

for key in JWT_SECRET AUTH_CSRF_SECRET AUTH_OUTBOX_ENCRYPTION_KEY \
  PII_ENCRYPTION_KEY AUDIT_INTEGRITY_KEY ENGAGEMENT_VISITOR_HMAC_SECRET; do
  value="$(read_value "$key")"
  if ((${#value} < 32)); then
    echo "$key must contain at least 32 characters" >&2
    exit 65
  fi
done

echo "preview environment contract is valid"
