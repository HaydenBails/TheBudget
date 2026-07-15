#!/usr/bin/env bash
#
# start-local.sh — start the Spending Tracker backend + frontend together.
#
#   API : uvicorn app.main:app  -> http://127.0.0.1:8787  (local-only)
#   Web : vite dev server        -> http://127.0.0.1:5173
#
# Prerequisites (see scripts/README.md):
#   - Python 3.11+ with a virtualenv at apps/api/.venv and deps installed
#   - Node 20+ with apps/web dependencies installed (npm install)
#
# Press Ctrl+C to stop both processes.
set -euo pipefail

# Resolve the repo root relative to this script so it works from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

API_HOST="${ST_HOST:-127.0.0.1}"
API_PORT="${ST_PORT:-8787}"
WEB_HOST="${ST_WEB_HOST:-127.0.0.1}"
WEB_PORT="${ST_WEB_PORT:-5173}"

# Require the documented API virtualenv so frontend/backend startup is atomic.
API_PY="${ROOT_DIR}/apps/api/.venv/bin/python"
if [[ ! -x "${API_PY}" ]]; then
  echo "error: API virtualenv not found at ${API_PY}" >&2
  echo "       See apps/api/README.md for setup instructions." >&2
  exit 1
fi

command -v npm >/dev/null 2>&1 || { echo "error: npm is not on PATH (Node.js 20+ is required)." >&2; exit 1; }
[[ -d "${ROOT_DIR}/apps/web/node_modules" ]] || {
  echo "error: frontend dependencies are not installed; run: cd apps/web && npm install" >&2
  exit 1
}
"${API_PY}" -c "import uvicorn" >/dev/null 2>&1 || {
  echo "error: API dependencies are not installed in apps/api/.venv." >&2
  echo "       Run: apps/api/.venv/bin/pip install -r apps/api/requirements.txt" >&2
  exit 1
}

# Kill both child processes when this script exits (Ctrl+C, error, etc.).
pids=()
cleanup() {
  echo
  echo "Stopping Spending Tracker (pids: ${pids[*]:-none})..."
  for pid in "${pids[@]:-}"; do
    [[ -n "${pid}" ]] && kill "${pid}" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "Starting API on http://${API_HOST}:${API_PORT} ..."
(
  cd "${ROOT_DIR}/apps/api"
  exec "${API_PY}" -m uvicorn app.main:app --reload --host "${API_HOST}" --port "${API_PORT}"
) &
pids+=("$!")

echo "Starting web dev server on http://${WEB_HOST}:${WEB_PORT} ..."
(
  cd "${ROOT_DIR}/apps/web"
  exec npm run dev -- --host "${WEB_HOST}" --port "${WEB_PORT}" --strictPort
) &
pids+=("$!")

echo "Both processes started. Press Ctrl+C to stop."
# Wait on whichever child exits first, then cleanup runs via the trap.
wait -n
