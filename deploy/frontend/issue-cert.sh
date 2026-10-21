#!/usr/bin/env bash
# Issue or renew the frontend certificate. The DNS A record must point at this
# instance's public address, and port 80 must be open, before the first issue.
#
#   sudo bash deploy/frontend/issue-cert.sh you@college.edu app.yourdomain.edu
#   sudo bash deploy/frontend/issue-cert.sh --renew
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
require_root
ENV_FILE=/etc/codelens/frontend.env

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Run deploy/frontend/setup.sh first." >&2
  exit 1
fi

if [[ "${1:-}" == "--renew" ]]; then
  certbot renew --webroot -w /var/www/certbot --quiet
  systemctl reload nginx
  echo "Renewal finished."
  exit 0
fi

EMAIL="${1:-}"
DOMAIN="${2:-}"
if [[ -z "$EMAIL" || -z "$DOMAIN" ]]; then
  echo "Usage: sudo bash deploy/frontend/issue-cert.sh you@college.edu app.yourdomain.edu" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a
upsert_env CODELENS_TLS 0 "$ENV_FILE"
upsert_env CODELENS_DOMAIN "$DOMAIN" "$ENV_FILE"
export CODELENS_TLS=0 CODELENS_DOMAIN="$DOMAIN"
bash "${ROOT_DIR}/render-nginx.sh"

certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --non-interactive \
  --keep-until-expiring

upsert_env CODELENS_TLS 1 "$ENV_FILE"
upsert_env CODELENS_DOMAIN "$DOMAIN" "$ENV_FILE"
export CODELENS_TLS=1
bash "${ROOT_DIR}/render-nginx.sh"
echo "HTTPS is on for ${DOMAIN}. Renew with: sudo bash deploy/frontend/issue-cert.sh --renew"
