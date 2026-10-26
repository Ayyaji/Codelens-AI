#!/usr/bin/env bash
# Write the frontend Nginx site. The browser loads the Vite build from this
# host and calls /api/... on the same origin. Nginx forwards that prefix to
# the backend private IP with the /api prefix removed.
set -euo pipefail

BACKEND_PRIVATE_IP="${BACKEND_PRIVATE_IP:-}"
DOMAIN="${CODELENS_DOMAIN:-_}"
TLS="${CODELENS_TLS:-0}"
OUT="${CODELENS_NGINX_OUT:-/etc/nginx/sites-available/codelens}"
WEB_ROOT="${CODELENS_WEB_ROOT:-/var/www/codelens}"

if [[ ! "$BACKEND_PRIVATE_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "Set BACKEND_PRIVATE_IP to the backend instance private IPv4 address." >&2
  exit 1
fi
if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "CODELENS_DOMAIN must be a hostname or _." >&2
  exit 1
fi

PROXY=$(cat <<EOF
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_pass http://${BACKEND_PRIVATE_IP}:8000/;
EOF
)

SITE=$(cat <<EOF
    client_max_body_size 3m;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /api/ {
${PROXY}
    }

    location = /index.html {
        root ${WEB_ROOT};
        add_header Cache-Control "no-cache";
    }

    location /assets/ {
        root ${WEB_ROOT};
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location / {
        root ${WEB_ROOT};
        try_files \$uri \$uri/ /index.html;
    }
EOF
)

mkdir -p "$(dirname "$OUT")"
{
  if [[ "$TLS" == "1" ]]; then
    cat <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};
    server_tokens off;

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

${SITE}
}
EOF
  else
    cat <<EOF
server {
    listen 80 default_server;
    server_name ${DOMAIN};
    server_tokens off;

${SITE}
}
EOF
  fi
} >"$OUT"

if [[ -n "${CODELENS_NGINX_RENDER_ONLY:-}" ]]; then
  exit 0
fi

if [[ "$TLS" == "1" ]]; then
  if [[ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
    echo "Certificate for ${DOMAIN} is missing. Run deploy/frontend/issue-cert.sh first." >&2
    exit 1
  fi
fi

ln -sfn "$OUT" /etc/nginx/sites-enabled/codelens
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
echo "Nginx is serving ${WEB_ROOT} and proxying /api/ to ${BACKEND_PRIVATE_IP}:8000"
