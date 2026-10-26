#!/usr/bin/env bash
# Rewrite the private IP after the database instance moves to the private subnet.
#   sudo bash deploy/mongo/refresh-ip.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
require_root
APP_ROOT="$(app_root)"
ENV_FILE=/opt/codelens/mongo.env

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

MONGO_PRIVATE_IP="$(private_ip)"
export MONGO_PRIVATE_IP
upsert_env MONGO_PRIVATE_IP "$MONGO_PRIVATE_IP" "$ENV_FILE"

umask 077
printf 'mongodb://%s:%s@%s:27017/codelens?authSource=admin\n' \
  "$MONGO_APP_USERNAME" "$MONGO_APP_PASSWORD" "$MONGO_PRIVATE_IP" >/opt/codelens/mongodb.uri
chmod 600 /opt/codelens/mongodb.uri

cd "$APP_ROOT"
docker compose -f deploy/mongo/docker-compose.yml up -d
echo "MongoDB is bound to ${MONGO_PRIVATE_IP}:27017."
echo "Store /opt/codelens/mongodb.uri as SSM /codelens/prod/MONGODB_URI, then shred -u /opt/codelens/mongodb.uri"
