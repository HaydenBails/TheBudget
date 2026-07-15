# start-local.ps1 — start the Spending Tracker backend + frontend together.
#
#   API : uvicorn app.main:app  -> http://127.0.0.1:8787  (local-only)
#   Web : vite dev server        -> http://127.0.0.1:5173
#
# Prerequisites (see scripts/README.md):
#   - Python 3.11+ with a virtualenv at apps\api\.venv and deps installed
#   - Node 20+ with apps\web dependencies installed (npm install)
#
# Press Ctrl+C to stop; this script also stops both child processes on exit.

$ErrorActionPreference = "Stop"

# Resolve the repo root relative to this script so it works from anywhere.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")

$ApiHost = if ($env:ST_HOST) { $env:ST_HOST } else { "127.0.0.1" }
$ApiPort = if ($env:ST_PORT) { $env:ST_PORT } else { "8787" }

# Prefer the API virtualenv's python if present; fall back to 'python' on PATH.
$ApiPy = Join-Path $RootDir "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $ApiPy)) {
    Write-Warning "$ApiPy not found; falling back to 'python' on PATH."
    Write-Host "  Create it with: cd apps\api; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    $ApiPy = "python"
}

$procs = @()
try {
    Write-Host "Starting API on http://${ApiHost}:${ApiPort} ..."
    $procs += Start-Process -PassThru -NoNewWindow -FilePath $ApiPy `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $ApiHost, "--port", $ApiPort) `
        -WorkingDirectory (Join-Path $RootDir "apps\api")

    Write-Host "Starting web dev server (apps\web) ..."
    $procs += Start-Process -PassThru -NoNewWindow -FilePath "npm" `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory (Join-Path $RootDir "apps\web")

    Write-Host "Both processes started. Press Ctrl+C to stop."
    # Block until either process exits.
    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
}
finally {
    Write-Host "`nStopping Spending Tracker..."
    foreach ($p in $procs) {
        if ($p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
