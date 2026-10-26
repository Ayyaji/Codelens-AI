#!/usr/bin/env bash
# One command for the MongoDB instance (Ubuntu 24.04, default VPC).
# Installs MongoDB 8, turns on auth, listens on the private IP only,
# and prints a MONGODB_URI the backend can use.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=deploy/lib.sh
source "$ROOT/deploy/lib.sh"
# shellcheck source=deploy/simple/lib.sh
source "$ROOT/deploy/simple/lib.sh"

require_root

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${VERSION_ID:-}" != "24.04" ]]; then
    echo "This script expects Ubuntu 24.04. This machine is ${PRETTY_NAME:-unknown}." >&2
    exit 1
  fi
fi

URI_FILE=/root/codelens-mongodb.uri
SECRET_FILE=/root/codelens-mongodb.admin
DB_NAME=codelens
APP_USER=codelens

if [[ -f "$URI_FILE" ]] && systemctl is-active --quiet mongod; then
  echo "MongoDB is already set up. Copy this URI into the backend setup:"
  echo
  cat "$URI_FILE"
  echo
  echo "The root password is in $SECRET_FILE."
  exit 0
fi

if [[ -f /etc/mongod.conf ]] && grep -q 'authorization: enabled' /etc/mongod.conf && [[ ! -f "$URI_FILE" ]]; then
  echo "MongoDB auth is already on, but $URI_FILE is missing." >&2
  echo "The URI was printed the first time this script succeeded. If that output is gone, reinstall MongoDB and run this again." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg

if ! command -v mongod >/dev/null 2>&1; then
  install -d -m 0755 /usr/share/keyrings
  curl -fsSL https://pgp.mongodb.com/server-8.0.asc \
    | gpg --batch --dearmor --yes -o /usr/share/keyrings/mongodb-server-8.0.gpg
  echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" \
    > /etc/apt/sources.list.d/mongodb-org-8.0.list
  apt-get update
  apt-get install -y mongodb-org
fi

systemctl enable mongod
systemctl start mongod

echo "Waiting for MongoDB to accept connections..."
ready=0
for _ in $(seq 1 60); do
  if mongosh --quiet --eval 'db.runCommand({ ping: 1 })' >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "MongoDB did not start. Check: journalctl -u mongod -n 50" >&2
  exit 1
fi

PRIVATE_IP="$(private_ip)"
ROOT_PASSWORD="$(openssl rand -hex 24)"
APP_PASSWORD="$(openssl rand -hex 24)"
URI="$(app_mongo_uri "$APP_PASSWORD" "$PRIVATE_IP" "$APP_USER" "$DB_NAME")"

install -d -m 0700 /root
umask 077
cat > /root/codelens-mongo-init.js <<EOF
const admin = db.getSiblingDB("admin");
if (!admin.getUser("root")) {
  admin.createUser({
    user: "root",
    pwd: "${ROOT_PASSWORD}",
    roles: [{ role: "root", db: "admin" }]
  });
}
if (!admin.getUser("${APP_USER}")) {
  admin.createUser({
    user: "${APP_USER}",
    pwd: "${APP_PASSWORD}",
    roles: [{ role: "readWrite", db: "${DB_NAME}" }]
  });
}
EOF
mongosh --quiet --file /root/codelens-mongo-init.js
rm -f /root/codelens-mongo-init.js

cat > /etc/mongod.conf <<EOF
storage:
  dbPath: /var/lib/mongodb
  wiredTiger:
    engineConfig:
      cacheSizeGB: 0.25
systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log
net:
  port: 27017
  bindIp: 127.0.0.1,${PRIVATE_IP}
processManagement:
  timeZoneInfo: /usr/share/zoneinfo
security:
  authorization: enabled
EOF

systemctl restart mongod

ready=0
for _ in $(seq 1 60); do
  if mongosh --quiet "$URI" --eval 'db.runCommand({ ping: 1 })' >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "MongoDB restarted but the app user could not sign in." >&2
  echo "Check: journalctl -u mongod -n 50" >&2
  exit 1
fi

printf '%s\n' "$URI" >"$URI_FILE"
chmod 600 "$URI_FILE"
cat >"$SECRET_FILE" <<EOF
ROOT_USER=root
ROOT_PASSWORD=${ROOT_PASSWORD}
APP_USER=${APP_USER}
APP_PASSWORD=${APP_PASSWORD}
PRIVATE_IP=${PRIVATE_IP}
MONGODB_URI=${URI}
EOF
chmod 600 "$SECRET_FILE"

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow OpenSSH
  ufw allow 27017/tcp
fi

echo
echo "MongoDB is ready."
echo "Private IP: $PRIVATE_IP"
echo "It listens on that address and on localhost. Port 27017 should stay closed to the internet."
echo
echo "Paste this into the backend setup as MONGODB_URI:"
echo
echo "$URI"
echo
echo "A copy is in $URI_FILE. The root password is in $SECRET_FILE."
