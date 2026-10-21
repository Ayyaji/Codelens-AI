#!/usr/bin/env bash
# Build the Chroma index inside the backend image.
# The running API already holds the embedding model. A second copy is enough
# to get the container killed on a t3.small, so this stops the API first.
# Running it twice appends duplicate chunks. To start over, stop the stack
# and delete the files in /opt/codelens/data/chroma, then run this again.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/../lib.sh"
APP_ROOT="$(app_root)"
ENV_FILE="${CODELENS_API_ENV:-/opt/codelens/backend.env}"
cd "$APP_ROOT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not available to this user. Re-run with sudo." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a
export BACKEND_PRIVATE_IP="${BACKEND_PRIVATE_IP:-$(private_ip)}"

echo "Stopping the API so the build is the only process loading the model..."
docker compose -f deploy/backend/docker-compose.yml stop api
docker compose -f deploy/backend/docker-compose.yml run --rm --no-deps api python -m rag_core.build_kb
docker compose -f deploy/backend/docker-compose.yml up -d

for _ in $(seq 1 120); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    curl -fsS "http://127.0.0.1:8000/health"
    echo
    echo "Knowledge base is ready at /opt/codelens/data/chroma"
    exit 0
  fi
  sleep 5
done
echo "The API did not come back. Recent logs:" >&2
docker compose -f deploy/backend/docker-compose.yml logs --tail 80 api >&2 || true
exit 1
