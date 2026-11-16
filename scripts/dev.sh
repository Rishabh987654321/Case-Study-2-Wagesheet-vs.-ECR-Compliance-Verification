#!/usr/bin/env bash
# Dev mode: backend with --reload in the background, frontend dev server (with HMR) in
# the foreground. Vite proxies /api to the backend (see frontend/vite.config.ts).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

cd "$ROOT_DIR/frontend"
npm install

echo "== Backend on http://localhost:${PORT:-8000} (reload), frontend dev server starting =="
npm run dev
