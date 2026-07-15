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

The launchers run a preflight check before starting either service. The API
virtualenv must exist with its dependencies installed (see
[`apps/api/README.md`](../apps/api/README.md)), and `apps/web` must have had
`npm install` run. If either child exits, the launcher stops the other one.
Press `Ctrl+C` to stop both.

```bash
./scripts/start-local.sh          # macOS / Linux
```

```powershell
./scripts/start-local.ps1         # Windows PowerShell
```

Run either script from any working directory. Optional environment variables
override the loopback addresses and ports:

| Variable      | Default     | Service |
| ------------- | ----------- | ------- |
| `ST_HOST`     | `127.0.0.1` | API     |
| `ST_PORT`     | `8787`      | API     |
| `ST_WEB_HOST` | `127.0.0.1` | Web     |
| `ST_WEB_PORT` | `5173`      | Web     |

Keep both hosts on `127.0.0.1` for the intended local-only privacy posture.
