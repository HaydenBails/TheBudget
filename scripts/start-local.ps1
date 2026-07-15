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
$WebHost = if ($env:ST_WEB_HOST) { $env:ST_WEB_HOST } else { "127.0.0.1" }
$WebPort = if ($env:ST_WEB_PORT) { $env:ST_WEB_PORT } else { "5173" }

# Require the documented API virtualenv so frontend/backend startup is atomic.
$ApiPy = Join-Path $RootDir "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $ApiPy)) {
    throw "API virtualenv not found at $ApiPy. See apps\api\README.md for setup instructions."
}

$Npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
if (-not $Npm) { $Npm = Get-Command "npm" -ErrorAction SilentlyContinue }
if (-not $Npm) { throw "npm is not on PATH (Node.js 20+ is required)." }
if (-not (Test-Path (Join-Path $RootDir "apps\web\node_modules"))) {
    throw "Frontend dependencies are not installed. Run: cd apps\web; npm install"
}
& $ApiPy -c "import uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "API dependencies are not installed in apps\api\.venv. See apps\api\README.md."
}

$procs = @()
try {
    Write-Host "Starting API on http://${ApiHost}:${ApiPort} ..."
    $procs += Start-Process -PassThru -NoNewWindow -FilePath $ApiPy `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", $ApiHost, "--port", $ApiPort) `
        -WorkingDirectory (Join-Path $RootDir "apps\api")

    Write-Host "Starting web dev server on http://${WebHost}:${WebPort} ..."
    $procs += Start-Process -PassThru -NoNewWindow -FilePath $Npm.Source `
        -ArgumentList @("run", "dev", "--", "--host", $WebHost, "--port", $WebPort, "--strictPort") `
        -WorkingDirectory (Join-Path $RootDir "apps\web")

    Write-Host "Both processes started. Press Ctrl+C to stop."
    # Stop the pair if either service exits.
    while (-not ($procs | Where-Object { $_.HasExited })) {
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host "`nStopping Spending Tracker..."
    foreach ($p in $procs) {
        if ($p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
