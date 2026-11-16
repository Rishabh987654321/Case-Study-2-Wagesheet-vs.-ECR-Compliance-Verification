#!/usr/bin/env bash
# Production-style run: install deps, build the frontend, serve everything from one port.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "== Backend setup =="
cd "$ROOT_DIR/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo "== Frontend build =="
cd "$ROOT_DIR/frontend"
npm install
npm run build

echo "== Starting server on port ${PORT:-8000} =="
cd "$ROOT_DIR/backend"
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
