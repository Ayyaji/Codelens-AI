#!/usr/bin/env bash
# Install Nginx on the frontend EC2 instance and deploy the current build.
# Run on that instance, from a clone of this repository:
#   sudo BACKEND_PRIVATE_IP=10.0.1.20 bash deploy/frontend/setup.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
require_root
link_app_root "$(app_root)"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx certbot curl ca-certificates
systemctl enable --now nginx

# Building the Vite app on a t3.micro can spike past 1 GiB because of the
# Monaco bundle. The swap file keeps that build from being killed. Copying a
# dist folder built on a laptop is still the faster path (see deploy.sh).
ensure_swap 2

mkdir -p /var/www/codelens /var/www/certbot /etc/codelens
if [[ ! -f /etc/codelens/frontend.env ]]; then
  touch /etc/codelens/frontend.env
  chmod 600 /etc/codelens/frontend.env
  upsert_env CODELENS_TLS 0 /etc/codelens/frontend.env
  upsert_env CODELENS_DOMAIN _ /etc/codelens/frontend.env
fi
if [[ -n "${BACKEND_PRIVATE_IP:-}" ]]; then
  upsert_env BACKEND_PRIVATE_IP "$BACKEND_PRIVATE_IP" /etc/codelens/frontend.env
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

bash "${ROOT_DIR}/deploy.sh"
echo "Frontend setup finished. Confirm with: curl -fsS -o /dev/null -w '%{http_code}\\n' http://127.0.0.1/"
