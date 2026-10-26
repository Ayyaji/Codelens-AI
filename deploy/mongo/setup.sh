#!/usr/bin/env bash
# Prepare the database instance and start MongoDB.
#
# Run this while the instance can reach the internet (launched in the public
# subnet with a public IPv4 address). Inbound is still closed by the security
# group. After the image is installed, move the instance into the private
# subnet with the procedure in docs/DEPLOY_AWS.md. A NAT gateway is the
# alternative that lets you launch it in the private subnet immediately.
#
#   sudo bash deploy/mongo/setup.sh
# The 20 GB data volume must already be attached. Set MONGO_DATA_DEVICE if it
# is not /dev/nvme1n1 or /dev/xvdf.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
require_root
APP_ROOT="$(app_root)"
link_app_root "$APP_ROOT"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git awscli xfsprogs
install_docker

DATA_DEV="${MONGO_DATA_DEVICE:-}"
if [[ -z "$DATA_DEV" ]]; then
  if [[ -b /dev/nvme1n1 ]]; then
    DATA_DEV=/dev/nvme1n1
  elif [[ -b /dev/xvdf ]]; then
    DATA_DEV=/dev/xvdf
  fi
fi
if [[ -z "$DATA_DEV" || ! -b "$DATA_DEV" ]]; then
  if [[ "${MONGO_ALLOW_ROOT_DISK:-0}" == "1" ]]; then
    echo "No extra volume found. Using the root disk because MONGO_ALLOW_ROOT_DISK=1."
    mkdir -p /opt/codelens/mongo/db
  else
    echo "No 20 GB data volume found at /dev/nvme1n1 or /dev/xvdf." >&2
    echo "Attach the gp3 volume, then re-run. Set MONGO_DATA_DEVICE if the name differs." >&2
    exit 1
  fi
else
  root_source="$(findmnt -n -o SOURCE / || true)"
  if [[ "$DATA_DEV" == "$root_source" || "$DATA_DEV" == /dev/nvme0n1 || "$DATA_DEV" == /dev/xvda ]]; then
    echo "Refusing to format ${DATA_DEV}; it looks like the root disk." >&2
    exit 1
  fi
  mkdir -p /opt/codelens/mongo
  if ! blkid "$DATA_DEV" >/dev/null 2>&1; then
    echo "Formatting ${DATA_DEV} as ext4."
    mkfs.ext4 -L codelens-mongo "$DATA_DEV"
  fi
  uuid="$(blkid -s UUID -o value "$DATA_DEV")"
  if ! grep -q "$uuid" /etc/fstab; then
    echo "UUID=${uuid} /opt/codelens/mongo ext4 defaults,nofail 0 2" >>/etc/fstab
  fi
  mountpoint -q /opt/codelens/mongo || mount /opt/codelens/mongo
  mkdir -p /opt/codelens/mongo/db
fi

if [[ ! -f /opt/codelens/mongo.env ]]; then
  if aws sts get-caller-identity --region "${AWS_REGION:-ap-south-1}" >/dev/null 2>&1; then
    bash "${ROOT_DIR}/fetch-env.sh" || true
  fi
fi
if [[ ! -f /opt/codelens/mongo.env ]]; then
  echo "No /opt/codelens/mongo.env yet." >&2
  echo "Create the SSM passwords (openssl rand -hex 24) and re-run, or write the file by hand." >&2
  exit 0
fi

# shellcheck disable=SC1090
set -a
source /opt/codelens/mongo.env
set +a
if [[ ! "${MONGO_APP_PASSWORD:-}" =~ ^[A-Za-z0-9]+$ ]]; then
  echo "MONGO_APP_PASSWORD must be alphanumeric. Generate one with: openssl rand -hex 24" >&2
  exit 1
fi
if [[ ! "${MONGO_INITDB_ROOT_PASSWORD:-}" =~ ^[A-Za-z0-9]+$ ]]; then
  echo "MONGO_INITDB_ROOT_PASSWORD must be alphanumeric." >&2
  exit 1
fi

MONGO_PRIVATE_IP="$(private_ip)"
export MONGO_PRIVATE_IP
upsert_env MONGO_PRIVATE_IP "$MONGO_PRIVATE_IP" /opt/codelens/mongo.env

cd "$APP_ROOT"
docker compose -f deploy/mongo/docker-compose.yml up -d

echo "Waiting for MongoDB to accept the application user..."
ok=0
for _ in $(seq 1 30); do
  if docker compose -f deploy/mongo/docker-compose.yml exec -T mongo \
    bash -lc 'mongosh --quiet --username "$MONGO_APP_USERNAME" --password "$MONGO_APP_PASSWORD" --authenticationDatabase admin --eval "db.getSiblingDB(\"codelens\").runCommand({ ping: 1 }).ok"' \
    | grep -q 1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" -ne 1 ]]; then
  echo "MongoDB did not answer. Recent logs:" >&2
  docker compose -f deploy/mongo/docker-compose.yml logs --tail 80 mongo >&2 || true
  exit 1
fi

umask 077
cat >/opt/codelens/mongodb.uri <<EOF
mongodb://${MONGO_APP_USERNAME}:${MONGO_APP_PASSWORD}@${MONGO_PRIVATE_IP}:27017/codelens?authSource=admin
EOF
chmod 600 /opt/codelens/mongodb.uri
echo "MongoDB is up on ${MONGO_PRIVATE_IP}:27017."
echo "The API connection string is in /opt/codelens/mongodb.uri (mode 600)."
echo "Store that string as the SSM parameter /codelens/prod/MONGODB_URI, then delete the file: shred -u /opt/codelens/mongodb.uri"
echo "After you move this instance to the private subnet its private IP changes. Update the URI and restart the backend."
