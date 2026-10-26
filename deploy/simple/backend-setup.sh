#!/usr/bin/env bash
# One command for the API instance (Ubuntu 24.04, 26.04, or newer; default VPC).
# Installs Docker, adds swap, writes /opt/codelens/backend.env, and starts
# the API behind Caddy so Vercel can call it over HTTPS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=deploy/lib.sh
source "$ROOT/deploy/lib.sh"
# shellcheck source=deploy/simple/lib.sh
source "$ROOT/deploy/simple/lib.sh"

require_root

warn_ubuntu_release

ENV_FILE=/opt/codelens/backend.env
HOST_FILE=/opt/codelens/public-host
COMPOSE_ENV=/opt/codelens/compose.env
COMPOSE=(docker compose --env-file "$COMPOSE_ENV" -f "$ROOT/deploy/simple/docker-compose.yml")

# Values passed on the command line win. Otherwise reuse the saved file.
uri_was_set=0
groq_was_set=0
keys_was_set=0
origin_was_set=0
domain_was_set=0
jwt_was_set=0
[[ -v MONGODB_URI ]] && uri_was_set=1
[[ -v GROQ_API_KEY ]] && groq_was_set=1
[[ -v GROQ_API_KEYS ]] && keys_was_set=1
[[ -v FRONTEND_ORIGIN ]] && origin_was_set=1
[[ -v DOMAIN ]] && domain_was_set=1
[[ -v JWT_SECRET ]] && jwt_was_set=1
passed_uri="${MONGODB_URI:-}"
passed_groq="${GROQ_API_KEY:-}"
passed_keys="${GROQ_API_KEYS:-}"
passed_origin="${FRONTEND_ORIGIN:-}"
passed_domain="${DOMAIN:-}"
passed_jwt="${JWT_SECRET:-}"

if [[ -f "$ENV_FILE" ]]; then
  echo "Using the saved settings in $ENV_FILE."
fi
if [[ "$uri_was_set" -eq 1 ]]; then
  MONGODB_URI="$passed_uri"
else
  MONGODB_URI="$(read_env MONGODB_URI "$ENV_FILE")"
fi
if [[ "$keys_was_set" -eq 1 ]]; then
  GROQ_KEYS_RAW="$passed_keys"
elif [[ "$groq_was_set" -eq 1 ]]; then
  GROQ_KEYS_RAW="$passed_groq"
else
  GROQ_KEYS_RAW="$(read_env GROQ_API_KEYS "$ENV_FILE")"
  if [[ -z "$GROQ_KEYS_RAW" ]]; then
    GROQ_KEYS_RAW="$(read_env GROQ_API_KEY "$ENV_FILE")"
  fi
fi
if [[ "$origin_was_set" -eq 1 ]]; then
  FRONTEND_ORIGIN="$passed_origin"
else
  FRONTEND_ORIGIN="$(read_env CORS_ORIGINS "$ENV_FILE")"
fi
if [[ "$domain_was_set" -eq 1 ]]; then
  DOMAIN="$passed_domain"
fi
if [[ "$jwt_was_set" -eq 1 ]]; then
  JWT_SECRET="$passed_jwt"
else
  JWT_SECRET="$(read_env JWT_SECRET "$ENV_FILE")"
fi

if [[ -z "${MONGODB_URI:-}" ]]; then
  if [[ ! -t 0 ]]; then
    echo "Set MONGODB_URI and run this again." >&2
    exit 1
  fi
  read -r -p "MONGODB_URI (the line mongo-setup.sh printed): " MONGODB_URI
fi
if [[ -z "${GROQ_KEYS_RAW:-}" ]]; then
  if [[ ! -t 0 ]]; then
    echo "Set GROQ_API_KEYS (comma-separated) or GROQ_API_KEY and run this again." >&2
    exit 1
  fi
  read -r -s -p "Groq API keys (one key, or 3 to 5 separated by commas): " GROQ_KEYS_RAW
  echo
fi
MONGODB_URI="$(trim "$MONGODB_URI")"
if ! mapfile -t GROQ_KEYS < <(normalize_groq_keys "$GROQ_KEYS_RAW"); then
  exit 1
fi
GROQ_API_KEY="${GROQ_KEYS[0]}"
GROQ_API_KEYS="$(IFS=,; printf '%s' "${GROQ_KEYS[*]}")"
if [[ -z "$MONGODB_URI" || -z "$GROQ_API_KEY" ]]; then
  echo "MONGODB_URI and a Groq API key are both required." >&2
  exit 1
fi
echo "Using ${#GROQ_KEYS[@]} Groq API key(s)."

if [[ -z "${DOMAIN:-}" && "$domain_was_set" -eq 0 && ! -f "$HOST_FILE" && -t 0 ]]; then
  read -r -p "Domain name (leave empty to use sslip.io): " DOMAIN || true
fi
DOMAIN="$(trim "${DOMAIN:-}")"
DOMAIN="${DOMAIN#https://}"
DOMAIN="${DOMAIN#http://}"
DOMAIN="${DOMAIN%%/*}"

if [[ "$origin_was_set" -eq 0 && -t 0 ]]; then
  read -r -p "Custom site origin (leave empty when the site is on vercel.app): " typed_origin || true
  if [[ -n "${typed_origin:-}" ]]; then
    FRONTEND_ORIGIN="$(trim "$typed_origin")"
    origin_was_set=1
  fi
fi
FRONTEND_ORIGIN="$(trim "${FRONTEND_ORIGIN:-}")"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN%/}"
if [[ -n "$FRONTEND_ORIGIN" && ! "$FRONTEND_ORIGIN" =~ ^https?://[^/]+$ ]]; then
  echo "FRONTEND_ORIGIN must look like https://your-site.example." >&2
  exit 1
fi

do_kb=0
if [[ "${BUILD_KB:-}" == "1" ]]; then
  do_kb=1
elif [[ "${BUILD_KB:-}" == "0" ]]; then
  do_kb=0
elif [[ -t 0 ]]; then
  if [[ -f /opt/codelens/data/chroma/chroma.sqlite3 ]]; then
    read -r -p "Rebuild the knowledge base? [y/N] " reply || true
    if [[ "${reply:-}" =~ ^[Yy]$ ]]; then
      do_kb=1
    fi
  else
    read -r -p "Build the knowledge base now? Answers stay empty until you do. [Y/n] " reply || true
    if [[ ! "${reply:-}" =~ ^[Nn]$ ]]; then
      do_kb=1
    fi
  fi
fi

do_teacher=0
if [[ "${CREATE_TEACHER:-}" == "1" ]]; then
  do_teacher=1
elif [[ "${CREATE_TEACHER:-}" == "0" ]]; then
  do_teacher=0
elif [[ -t 0 ]]; then
  read -r -p "Create a teacher account now? [y/N] " reply || true
  if [[ "${reply:-}" =~ ^[Yy]$ ]]; then
    do_teacher=1
  fi
fi

if [[ "$do_teacher" -eq 1 ]]; then
  if [[ -z "${TEACHER_NAME:-}" ]]; then
    [[ -t 0 ]] || { echo "Set TEACHER_NAME, TEACHER_EMAIL, and TEACHER_PASSWORD." >&2; exit 1; }
    read -r -p "Teacher name: " TEACHER_NAME
  fi
  if [[ -z "${TEACHER_EMAIL:-}" ]]; then
    [[ -t 0 ]] || { echo "Set TEACHER_EMAIL and TEACHER_PASSWORD." >&2; exit 1; }
    read -r -p "Teacher email: " TEACHER_EMAIL
  fi
  TEACHER_NAME="$(trim "$TEACHER_NAME")"
  TEACHER_EMAIL="$(trim "$TEACHER_EMAIL")"
  TEACHER_PASSWORD="${TEACHER_PASSWORD:-}"
  while [[ "${#TEACHER_PASSWORD}" -lt 8 ]]; do
    if [[ ! -t 0 ]]; then
      echo "TEACHER_PASSWORD must be at least 8 characters." >&2
      exit 1
    fi
    read -r -s -p "Teacher password (at least 8 characters): " TEACHER_PASSWORD
    echo
    TEACHER_PASSWORD="$(trim "$TEACHER_PASSWORD")"
  done
fi

# Prefer an explicit domain. Otherwise follow the current public IP when the
# saved sslip.io name no longer matches the Elastic IP.
if [[ -n "${DOMAIN:-}" ]]; then
  PUBLIC_HOST="$DOMAIN"
else
  current_ip="$(public_ip)"
  current_sslip="$(sslip_host "$current_ip")"
  if [[ "${USE_SSLIP:-}" == "1" || ! -f "$HOST_FILE" ]]; then
    PUBLIC_HOST="$current_sslip"
  else
    saved="$(tr -d '[:space:]' <"$HOST_FILE")"
    if [[ "$saved" == *.sslip.io && "$saved" != "$current_sslip" ]]; then
      echo "The public IP changed. The API address is now https://$current_sslip"
      echo "Update VITE_API_URL on Vercel to that address."
      PUBLIC_HOST="$current_sslip"
    else
      PUBLIC_HOST="$saved"
    fi
  fi
fi

echo "Installing Docker and adding 4 GiB of swap..."
ensure_swap 4
install_docker

free_kb="$(df -Pk / | awk 'NR==2 {print $4}')"
if [[ "$free_kb" -lt 8000000 ]]; then
  echo "Less than 8 GB is free on /. The API image needs more disk." >&2
  exit 1
fi

install -d -m 0755 /opt/codelens
install -d -o 10001 -g 10001 /opt/codelens/data/chroma /opt/codelens/cache/huggingface
install -d -m 0755 /opt/codelens/caddy/data /opt/codelens/caddy/config

if [[ -z "${JWT_SECRET:-}" ]]; then
  JWT_SECRET="$(openssl rand -base64 48 | tr -d '\n')"
fi

if [[ -z "${MONGODB_DB:-}" ]]; then
  MONGODB_DB="$(read_env MONGODB_DB "$ENV_FILE")"
fi
MONGODB_DB="${MONGODB_DB:-codelens}"

touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
write_env GROQ_API_KEY "$GROQ_API_KEY" "$ENV_FILE"
write_env GROQ_API_KEYS "$GROQ_API_KEYS" "$ENV_FILE"
write_env JWT_SECRET "$JWT_SECRET" "$ENV_FILE"
write_env MONGODB_URI "$MONGODB_URI" "$ENV_FILE"
write_env MONGODB_DB "${MONGODB_DB:-codelens}" "$ENV_FILE"
write_env CODELENS_LOW_MEMORY 1 "$ENV_FILE"
write_env CORS_ORIGIN_REGEX "$VERCEL_ORIGIN_REGEX" "$ENV_FILE"
if [[ -n "$FRONTEND_ORIGIN" ]]; then
  write_env CORS_ORIGINS "$FRONTEND_ORIGIN" "$ENV_FILE"
elif [[ "$origin_was_set" -eq 1 ]]; then
  tmp="$(mktemp)"
  grep -v '^CORS_ORIGINS=' "$ENV_FILE" >"$tmp" || true
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

printf 'PUBLIC_HOST=%s\n' "$PUBLIC_HOST" >"$COMPOSE_ENV"
chmod 600 "$COMPOSE_ENV"
printf '%s\n' "$PUBLIC_HOST" >"$HOST_FILE"
chmod 644 "$HOST_FILE"

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
fi

cd "$ROOT/deploy/simple"
up_args=(up -d --force-recreate)
if [[ "${REBUILD:-0}" == "1" ]] || ! docker image inspect codelens-api:prod >/dev/null 2>&1; then
  up_args+=(--build)
  echo "Building the API image. The first build downloads PyTorch and can take a while."
fi
"${COMPOSE[@]}" "${up_args[@]}"

wait_for_api() {
  echo "Waiting for the API. The first boot loads the embedding model and can take several minutes."
  local _i
  for _i in $(seq 1 120); do
    if curl -fsS --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
      echo "API is up."
      return 0
    fi
    sleep 5
  done
  echo "The API did not become healthy. Last logs:" >&2
  "${COMPOSE[@]}" logs api --tail 80 >&2 || true
  return 1
}

wait_for_api

if [[ "$do_kb" -eq 1 ]]; then
  echo "Stopping the API so the knowledge-base build can use the memory."
  "${COMPOSE[@]}" stop api
  "${COMPOSE[@]}" run --rm --no-deps api python -m rag_core.build_kb
  "${COMPOSE[@]}" up -d api
  wait_for_api
fi

if [[ "$do_teacher" -eq 1 ]]; then
  "${COMPOSE[@]}" exec -T api python -m rag_core.create_teacher \
    --name "$TEACHER_NAME" \
    --email "$TEACHER_EMAIL" \
    --password "$TEACHER_PASSWORD"
fi

echo
echo "Checking https://${PUBLIC_HOST}/health"
https_ok=0
for _i in $(seq 1 24); do
  if curl -fsS --max-time 15 "https://${PUBLIC_HOST}/health"; then
    echo
    https_ok=1
    break
  fi
  sleep 5
done

echo
echo "API address: https://${PUBLIC_HOST}"
echo
echo "On Vercel, set the environment variable:"
echo "  VITE_API_URL=https://${PUBLIC_HOST}"
echo "Root Directory: frontend"
echo "Every https://*.vercel.app site is allowed to call this API."
if [[ -n "$FRONTEND_ORIGIN" ]]; then
  echo "Also allowed: $FRONTEND_ORIGIN"
fi
if [[ "$https_ok" -ne 1 ]]; then
  echo
  echo "The local API answered, but https://${PUBLIC_HOST}/health did not." >&2
  echo "Check that the Elastic IP is attached and that ports 80 and 443 are open to the internet." >&2
  exit 1
fi
