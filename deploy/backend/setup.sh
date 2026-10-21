#!/usr/bin/env bash
# First-time setup for the backend EC2 instance (t3.small, public subnet).
#   sudo bash deploy/backend/setup.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
require_root
link_app_root "$(app_root)"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git awscli python3
install_docker
ensure_swap 2

mkdir -p /opt/codelens/data/chroma /opt/codelens/cache/huggingface
chown -R 10001:10001 /opt/codelens/data /opt/codelens/cache

IP="$(private_ip)"
echo "Private IP of this instance: ${IP}"
echo "The frontend Nginx must proxy /api to this address. The security group allows port 8000 only from the frontend group."

if [[ ! -f /opt/codelens/backend.env ]]; then
  if aws sts get-caller-identity --region "${AWS_REGION:-ap-south-1}" >/dev/null 2>&1; then
    bash "${ROOT_DIR}/fetch-env.sh" || true
  fi
fi
if [[ ! -f /opt/codelens/backend.env ]]; then
  echo "No /opt/codelens/backend.env yet. Create the SSM parameters, then run: sudo bash deploy/backend/deploy.sh" >&2
  exit 0
fi

upsert_env BACKEND_PRIVATE_IP "$IP" /opt/codelens/backend.env
bash "${ROOT_DIR}/deploy.sh"
echo "Swap: $(swapon --show | tr '\n' ' ')"
echo "Memory: $(free -h | awk 'NR==2 {print $2 " total, " $7 " available"}')"
