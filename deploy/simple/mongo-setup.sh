#!/usr/bin/env bash
# One command for the MongoDB instance (Ubuntu 24.04, 26.04, or newer).
# Runs MongoDB 8 in Docker, turns on auth, publishes 27017 on the private IP
# only, and prints a MONGODB_URI the backend can use.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=deploy/lib.sh
source "$ROOT/deploy/lib.sh"
# shellcheck source=deploy/simple/lib.sh
source "$ROOT/deploy/simple/lib.sh"

require_root
warn_ubuntu_release

URI_FILE=/root/codelens-mongodb.uri
SECRET_FILE=/root/codelens-mongodb.admin
DATA_DIR=/var/lib/codelens-mongo
CONTAINER=codelens-mongo
IMAGE=mongo:8
DB_NAME=codelens
APP_USER=codelens

container_running() {
  [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" == "true" ]]
}

published_on_private_ip() {
  local have=""
  have="$(docker port "$CONTAINER" 27017/tcp 2>/dev/null || true)"
  [[ "$have" == "${PRIVATE_IP}:27017" ]]
}

data_initialized() {
  [[ -d "$DATA_DIR/journal" || -f "$DATA_DIR/WiredTiger" || -f "$DATA_DIR/mongod.lock" ]]
}

print_uri() {
  echo "MongoDB is ready."
  echo "Private IP: $PRIVATE_IP"
  echo "Port 27017 is published on that address only."
  echo
  echo "Paste this into the backend setup as MONGODB_URI:"
  echo
  echo "$URI"
  echo
  echo "A copy is in $URI_FILE. The root password is in $SECRET_FILE."
}

load_passwords() {
  ROOT_PASSWORD="$(read_env ROOT_PASSWORD "$SECRET_FILE")"
  APP_PASSWORD="$(read_env APP_PASSWORD "$SECRET_FILE")"
  [[ -n "$ROOT_PASSWORD" && -n "$APP_PASSWORD" ]]
}

save_secrets() {
  install -d -m 0700 /root
  umask 077
  cat >"$SECRET_FILE" <<EOF
ROOT_USER=root
ROOT_PASSWORD=${ROOT_PASSWORD}
APP_USER=${APP_USER}
APP_PASSWORD=${APP_PASSWORD}
PRIVATE_IP=${PRIVATE_IP}
EOF
  chmod 600 "$SECRET_FILE"
}

ensure_container() {
  if container_running && published_on_private_ip; then
    return 0
  fi
  if docker inspect "$CONTAINER" >/dev/null 2>&1; then
    docker rm -f "$CONTAINER" >/dev/null
  fi
  docker pull "$IMAGE"
  docker run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    --publish "${PRIVATE_IP}:27017:27017" \
    --volume "${DATA_DIR}:/data/db" \
    --env MONGO_INITDB_ROOT_USERNAME=root \
    --env MONGO_INITDB_ROOT_PASSWORD="$ROOT_PASSWORD" \
    "$IMAGE" \
    --wiredTigerCacheSizeGB 0.25
}

wait_for_mongo() {
  local _i
  for _i in $(seq 1 60); do
    if docker exec "$CONTAINER" mongosh --quiet \
      -u root -p "$ROOT_PASSWORD" --authenticationDatabase admin \
      --eval 'db.runCommand({ ping: 1 })' >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "MongoDB did not accept the root user. Last logs:" >&2
  docker logs "$CONTAINER" --tail 50 >&2 || true
  return 1
}

create_app_user() {
  docker exec -i "$CONTAINER" mongosh --quiet \
    -u root -p "$ROOT_PASSWORD" --authenticationDatabase admin <<EOF
const admin = db.getSiblingDB("admin");
if (!admin.getUser("${APP_USER}")) {
  admin.createUser({
    user: "${APP_USER}",
    pwd: "${APP_PASSWORD}",
    roles: [{ role: "readWrite", db: "${DB_NAME}" }]
  });
}
EOF
}

export DEBIAN_FRONTEND=noninteractive
install_docker

PRIVATE_IP="$(private_ip)"
# The official image runs mongod as uid 999. Recreating the directory on a
# second run is safe; chown fixes a partial run that left it owned by root.
install -d -o 999 -g 999 -m 0755 "$DATA_DIR"

if [[ -f "$URI_FILE" ]] && container_running && published_on_private_ip; then
  URI="$(tr -d '[:space:]' <"$URI_FILE")"
  echo "MongoDB is already set up. Copy this URI into the backend setup:"
  echo
  echo "$URI"
  echo
  echo "The root password is in $SECRET_FILE."
  exit 0
fi

if [[ -f "$SECRET_FILE" ]] && load_passwords; then
  echo "Reusing the passwords in $SECRET_FILE."
elif data_initialized; then
  echo "MongoDB data is already in $DATA_DIR but $SECRET_FILE is missing." >&2
  echo "The script will not reset that password. Restore the secret file or remove $DATA_DIR before a fresh install." >&2
  exit 1
else
  ROOT_PASSWORD="$(openssl rand -hex 24)"
  APP_PASSWORD="$(openssl rand -hex 24)"
  save_secrets
fi

URI="$(app_mongo_uri "$APP_PASSWORD" "$PRIVATE_IP" "$APP_USER" "$DB_NAME")"
ensure_container
wait_for_mongo
create_app_user

ready=0
for _ in $(seq 1 30); do
  if docker exec "$CONTAINER" mongosh --quiet \
    "mongodb://${APP_USER}:${APP_PASSWORD}@127.0.0.1:27017/${DB_NAME}?authSource=admin" \
    --eval 'db.runCommand({ ping: 1 })' >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "The app user could not sign in. Last logs:" >&2
  docker logs "$CONTAINER" --tail 50 >&2 || true
  exit 1
fi

printf '%s\n' "$URI" >"$URI_FILE"
chmod 600 "$URI_FILE"
save_secrets

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow OpenSSH
  ufw allow 27017/tcp
fi

echo
print_uri
