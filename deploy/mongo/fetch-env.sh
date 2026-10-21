#!/usr/bin/env bash
# Write /opt/codelens/mongo.env from SSM. Values are never printed.
#   /codelens/prod/MONGO_ROOT_PASSWORD   SecureString, alphanumeric
#   /codelens/prod/MONGO_APP_PASSWORD    SecureString, alphanumeric
#   /codelens/prod/MONGO_APP_USERNAME    optional, default codelens
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"

PREFIX="${SSM_PREFIX:-/codelens/prod}"
DEST="${CODELENS_MONGO_ENV:-/opt/codelens/mongo.env}"
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

put_required MONGO_ROOT_PASSWORD
put_required MONGO_APP_PASSWORD

app_user="codelens"
if value="$(read_ssm "${PREFIX}/MONGO_APP_USERNAME" 2>/dev/null)"; then
  if [[ -n "$value" && "$value" != "None" ]]; then
    app_user="$value"
  fi
fi
upsert_env MONGO_INITDB_ROOT_USERNAME root "$DEST"
# The root password variable expected by the mongo image is the init name.
root_password="$(read_ssm "${PREFIX}/MONGO_ROOT_PASSWORD")"
upsert_env MONGO_INITDB_ROOT_PASSWORD "$root_password" "$DEST"
upsert_env MONGO_APP_USERNAME "$app_user" "$DEST"
unset root_password
echo "Mongo env is ${DEST} (mode 600). The root password was copied to MONGO_INITDB_ROOT_PASSWORD."
