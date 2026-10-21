#!/usr/bin/env bash
# Publish the Vite build and reload Nginx.
#   sudo bash deploy/frontend/deploy.sh
#   sudo DIST_SRC=/tmp/codelens-dist bash deploy/frontend/deploy.sh
#
# VITE_API_URL defaults to /api so the browser calls this same host.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
require_root
APP_ROOT="$(app_root)"
ENV_FILE=/etc/codelens/frontend.env

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

export VITE_API_URL="${VITE_API_URL:-/api}"
export VITE_USE_MOCKS=false
export VITE_MOCK_ENDPOINTS=

SRC="${DIST_SRC:-${APP_ROOT}/frontend/dist}"
if [[ ! -f "${SRC}/index.html" ]]; then
  echo "No build at ${SRC}. Building on this machine with VITE_API_URL=${VITE_API_URL}."
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is not installed. Run deploy/frontend/setup.sh, or copy a dist folder and set DIST_SRC." >&2
    exit 1
  fi
  cd "${APP_ROOT}/frontend"
  npm ci
  npm run build
  SRC="${APP_ROOT}/frontend/dist"
fi

mkdir -p /var/www/codelens
find /var/www/codelens -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -a "${SRC}/." /var/www/codelens/
chown -R www-data:www-data /var/www/codelens

if [[ -z "${BACKEND_PRIVATE_IP:-}" ]]; then
  echo "BACKEND_PRIVATE_IP is not set. Write it to ${ENV_FILE} and run this again." >&2
  exit 1
fi
export BACKEND_PRIVATE_IP CODELENS_DOMAIN="${CODELENS_DOMAIN:-_}" CODELENS_TLS="${CODELENS_TLS:-0}"
bash "${ROOT_DIR}/render-nginx.sh"
echo "Frontend deployed. API base baked into the build: ${VITE_API_URL}"
