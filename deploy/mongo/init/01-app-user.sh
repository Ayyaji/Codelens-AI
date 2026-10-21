#!/bin/bash
# Runs once, when the data directory is empty. Creates the application user
# the API uses. The password comes from the container environment, not from
# this file. Use an alphanumeric password (openssl rand -hex 24).
set -euo pipefail

if [[ -z "${MONGO_APP_USERNAME:-}" || -z "${MONGO_APP_PASSWORD:-}" ]]; then
  echo "MONGO_APP_USERNAME and MONGO_APP_PASSWORD are required." >&2
  exit 1
fi
if [[ ! "$MONGO_APP_USERNAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "MONGO_APP_USERNAME must be alphanumeric." >&2
  exit 1
fi
if [[ ! "$MONGO_APP_PASSWORD" =~ ^[A-Za-z0-9]+$ ]]; then
  echo "MONGO_APP_PASSWORD must be alphanumeric so it is safe in the URI and in this script." >&2
  exit 1
fi

mongosh --quiet \
  --username "$MONGO_INITDB_ROOT_USERNAME" \
  --password "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin <<EOF
db.getSiblingDB("admin").createUser({
  user: "${MONGO_APP_USERNAME}",
  pwd: "${MONGO_APP_PASSWORD}",
  roles: [{ role: "readWrite", db: "codelens" }]
})
EOF
