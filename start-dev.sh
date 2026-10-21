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
  echo "Created .env. Set GROQ_API_KEY in that file before model calls will succeed."
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
