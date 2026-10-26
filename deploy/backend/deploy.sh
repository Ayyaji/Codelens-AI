#!/usr/bin/env bash
# Rebuild and restart the API container.
#   sudo bash deploy/backend/deploy.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
APP_ROOT="$(app_root)"
ENV_FILE="${CODELENS_API_ENV:-/opt/codelens/backend.env}"
cd "$APP_ROOT"

if [[ -d .git ]]; then
  git config --global --add safe.directory "$APP_ROOT" || true
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Run deploy/backend/fetch-env.sh or write the file by hand." >&2
  exit 1
fi

python3 - "$ENV_FILE" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
values = {}
for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    values[key] = value
missing = [key for key in ("GROQ_API_KEY", "JWT_SECRET", "MONGODB_URI") if not values.get(key)]
if missing:
    sys.exit("Missing keys in the env file: " + ", ".join(missing))
secret = values["JWT_SECRET"]
if secret == "change-me-to-a-long-random-string" or len(secret) < 32:
    sys.exit("JWT_SECRET must be a random string of at least 32 characters.")
uri = values["MONGODB_URI"]
if "localhost" in uri or "127.0.0.1" in uri:
    sys.exit("MONGODB_URI points at this machine. Use the MongoDB instance private IP, or an Atlas URI.")
print("Env file ok. JWT length", len(secret), ".")
PY

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not available to this user. Re-run with sudo." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a
if [[ -z "${BACKEND_PRIVATE_IP:-}" ]]; then
  BACKEND_PRIVATE_IP="$(private_ip)"
  export BACKEND_PRIVATE_IP
fi

if [[ "$(id -u)" -eq 0 ]]; then
  mkdir -p /opt/codelens/data/chroma /opt/codelens/cache/huggingface
  chown -R 10001:10001 /opt/codelens/data /opt/codelens/cache
fi

export DOCKER_BUILDKIT=1
docker compose -f deploy/backend/docker-compose.yml build
docker compose -f deploy/backend/docker-compose.yml up -d --remove-orphans

echo "Waiting for http://127.0.0.1:8000/health (the first boot downloads the embedding model)..."
ok=0
for _ in $(seq 1 120); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 5
done
if [[ "$ok" -ne 1 ]]; then
  echo "The API did not become healthy. Recent logs:" >&2
  docker compose -f deploy/backend/docker-compose.yml logs --tail 80 api >&2 || true
  exit 1
fi
curl -fsS "http://127.0.0.1:8000/health"
echo
echo "API is listening on ${BACKEND_PRIVATE_IP}:8000 and on 127.0.0.1:8000."
