# Scripts

Convenience launchers that start the backend and frontend together for local
development.

| Script            | Platform            |
| ----------------- | ------------------- |
| `start-local.sh`  | macOS / Linux (bash)|
| `start-local.ps1` | Windows (PowerShell)|

Both start:

- **API** — `uvicorn app.main:app` on `http://127.0.0.1:8787`
- **Web** — Vite dev server (`npm run dev`) in `apps/web` (defaults to `:5173`)

## Prerequisites

- **Node.js** 20+ (frontend; `apps/web` dependencies installed via `npm install`)
- **Python** 3.11+ (backend; virtualenv at `apps/api/.venv`)

The scripts assume the API virtualenv already exists and dependencies are
installed (see [`apps/api/README.md`](../apps/api/README.md)) and that
`apps/web` has had `npm install` run. They are simple and readable rather than
bulletproof — press `Ctrl+C` to stop.

```bash
./scripts/start-local.sh          # macOS / Linux
```

```powershell
./scripts/start-local.ps1         # Windows PowerShell
```
