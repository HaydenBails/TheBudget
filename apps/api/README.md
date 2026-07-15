# Spending Tracker API

Local-first FastAPI backend for the Spending Tracker. **Stage 0 placeholder** —
it exposes only service metadata and a health probe. Domain models, migrations,
and statement parsing arrive in later stages.

> The API binds to `127.0.0.1` (loopback) by design and has **no
> authentication**. It is a single-user, local-only desktop service.

## Requirements

- Python 3.11+ (the product plan targets 3.12/3.13; 3.11 works for Stage 0)

## Setup

```bash
cd apps/api
python -m venv .venv

# Activate the virtualenv:
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -r requirements.txt
# For tests + lint:
pip install -r requirements-dev.txt
```

## Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

- `GET /`        → `{ "name", "version", "status" }`
- `GET /health`  → `{ "status": "ok", "service": "spending-tracker-api", "version": "0.0.1" }`
- `GET /docs`    → interactive OpenAPI (Swagger) UI

Add `--reload` during development for auto-restart on file changes.

## Configuration

Settings load from environment variables prefixed `ST_` and an optional `.env`
file (copy `.env.example` → `.env`). See [`app/config.py`](app/config.py).

| Variable   | Default       | Description                          |
| ---------- | ------------- | ------------------------------------ |
| `ST_HOST`  | `127.0.0.1`   | Bind address (keep on loopback).     |
| `ST_PORT`  | `8787`        | Bind port.                           |
| `ST_DATABASE_PATH` | `data/spending_tracker.db` | Local SQLite database file. |

## Database migrations

Run migrations from `apps/api` with the virtual environment active. Alembic
uses `ST_DATABASE_PATH`, so the same commands work for the default local store
or an explicitly selected database:

```bash
# Apply every migration
python -m alembic upgrade head

# Show the current and available revisions
python -m alembic current
python -m alembic history

# Roll back one revision, then reapply it
python -m alembic downgrade -1
python -m alembic upgrade head
```

For a temporary or test database, set the path before running Alembic:

```bash
ST_DATABASE_PATH=/tmp/spending-tracker-test.db python -m alembic upgrade head
```

```powershell
$env:ST_DATABASE_PATH = "$env:TEMP\spending-tracker-test.db"
python -m alembic upgrade head
```

Create future revisions only after importing the relevant ORM metadata in
`alembic/env.py`:

```bash
python -m alembic revision --autogenerate -m "describe schema change"
```

## Test & lint

```bash
python -m pytest -q
ruff check .
```

## Layout

```
apps/api/
  app/
    main.py            # FastAPI app + CORS + router wiring
    config.py          # pydantic-settings Settings
    routers/
      health.py        # /health probe
      # profiles.py, accounts.py, imports.py, ... (future stages)
  tests/
    test_health.py
  requirements.txt        # runtime deps
  requirements-dev.txt     # test/lint deps
  pyproject.toml           # ruff + pytest config
  .env.example
```
