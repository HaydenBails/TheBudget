#!/usr/bin/env bash
#
# Run the Spending Tracker with PYTHON ONLY — no Node.js required.
#
# The web UI is pre-built into apps/web/dist/ (committed) and served by the
# FastAPI backend, so this single local Python process serves both the app and
# the API on http://127.0.0.1:8787.
#
# Prerequisites: Python 3.11+ (that's it — no Node).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/api"

# Create the local virtualenv on first run.
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing backend dependencies…"
pip install -q -r requirements.txt

echo "Applying database migrations…"
python -m alembic upgrade head

URL="http://127.0.0.1:8787"
echo "Opening $URL"
# Open the browser shortly after the server starts (best-effort).
(
  sleep 2
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  fi
) >/dev/null 2>&1 &

echo "Starting Spending Tracker on $URL (Ctrl+C to stop)…"
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
