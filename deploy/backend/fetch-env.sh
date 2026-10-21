#!/usr/bin/env bash
# Write /opt/codelens/backend.env from SSM. Values are never printed.
# Parameters (SecureString unless noted):
#   /codelens/prod/GROQ_API_KEY
#   /codelens/prod/JWT_SECRET
#   /codelens/prod/MONGODB_URI
#   /codelens/prod/MONGODB_DB          optional, default codelens
#   /codelens/prod/CORS_ORIGINS        optional, used by the S3 alternative
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"

PREFIX="${SSM_PREFIX:-/codelens/prod}"
DEST="${CODELENS_API_ENV:-/opt/codelens/backend.env}"
mkdir -p /opt/codelens
touch "$DEST"
chmod 600 "$DEST"

put_required() {
  local key="$1"
  local name="${PREFIX}/${key}"
  local value
  if ! value="$(read_ssm "$name" 2>/dev/null)"; then
    echo "Missing SSM parameter ${name}." >&2
    exit 1
  fi
  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "SSM parameter ${name} is empty." >&2
    exit 1
  fi
  upsert_env "$key" "$value" "$DEST"
  echo "Wrote ${key} from ${name}"
}

put_optional() {
  local key="$1"
  local name="${PREFIX}/${key}"
  local value
  if ! value="$(read_ssm "$name" 2>/dev/null)"; then
    echo "Skipped optional ${name}"
    return 0
  fi
  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "Skipped empty ${name}"
    return 0
  fi
  upsert_env "$key" "$value" "$DEST"
  echo "Wrote ${key} from ${name}"
}

put_required GROQ_API_KEY
put_required JWT_SECRET
put_required MONGODB_URI
put_optional MONGODB_DB
put_optional CORS_ORIGINS
if ! grep -q '^MONGODB_DB=' "$DEST"; then
  upsert_env MONGODB_DB codelens "$DEST"
fi
echo "Backend env is ${DEST} (mode 600)."
