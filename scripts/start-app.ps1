# Run the Spending Tracker with PYTHON ONLY - no Node.js required.
#
# The web UI is pre-built into apps\web\dist\ (committed) and served by the
# FastAPI backend, so this single local Python process serves both the app and
# the API on http://127.0.0.1:8787.
#
# Prerequisites: Python 3.11+ (that's it - no Node).
$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\.."
Set-Location "$root\apps\api"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

Write-Host "Installing backend dependencies..."
pip install -q -r requirements.txt

Write-Host "Applying database migrations..."
python -m alembic upgrade head

$url = "http://127.0.0.1:8787"
Write-Host "Opening $url"
Start-Process $url

Write-Host "Starting Spending Tracker on $url (Ctrl+C to stop)..."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
