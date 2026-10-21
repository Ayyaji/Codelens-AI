#!/usr/bin/env bash
# Start the CodeLens API (port 8000) and the Vite client (port 5173).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env. Set GROQ_API_KEY and JWT_SECRET in that file before model calls and shared logins will succeed."
fi

ensure_env() {
  local name="$1" value="$2"
  if ! grep -q "^${name}=" .env; then
    echo "${name}=${value}" >> .env
    echo "Added ${name} to .env"
  fi
}
ensure_env MONGODB_URI "mongodb://localhost:27017"
ensure_env MONGODB_DB codelens
ensure_env JWT_SECRET change-me-to-a-long-random-string

mongo_up() {
  (echo >/dev/tcp/127.0.0.1/27017) >/dev/null 2>&1
}

if ! mongo_up; then
  if command -v docker >/dev/null 2>&1; then
    echo "MongoDB is not on port 27017. Starting it with docker compose..."
    docker compose up -d || true
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
      if mongo_up; then
        break
      fi
      sleep 1
    done
  fi
  if ! mongo_up; then
    echo "MongoDB is not listening on localhost:27017."
    echo "Install MongoDB Community Server, or run: docker compose up -d"
  fi
else
  echo "MongoDB is listening on localhost:27017"
fi

if [[ ! -d codelens_kb ]]; then
  echo "Building the debugging knowledge base (first run downloads the embedding model)..."
  if ! python -m rag_core.build_kb; then
    echo "Knowledge base build failed. POST /ask can still run, but debugging answers will have no retrieved notes."
  fi
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    pkill -P "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

python -m uvicorn rag_core.api:app --reload --port 8000 &
BACKEND_PID=$!

cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "API:    http://localhost:8000"
echo "Client: http://localhost:5173"
npm run dev
