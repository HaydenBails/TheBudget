# Spending Tracker (working title)

> **Contributors and AI agents:** read
> [`docs/implementation-workboard.md`](docs/implementation-workboard.md) before
> making changes. It is the source of truth for task ownership, dependencies,
> progress, and handoffs.

A polished, desktop-first, **local-first** personal spending tracker. It imports
text-based credit-card statements, normalizes them into transactions, suggests
categories, learns from your corrections, detects recurring charges, and turns
raw statement data into clear spending and savings insights.

> **Status:** Stage 2 foundation complete. The **Meridian** UI direction is the
> production design. Two production vertical slices — **profiles/accounts** and
> **categories** (with default seeding) — are built end-to-end (FastAPI + SQLite
> + Alembic backend, a Meridian production app at `/app` backed by TanStack
> Query) and validated (backend + frontend tests, migrations, profile
> isolation). Transactions, statement parsing, and analytics are still upcoming
> — see the product plan and `docs/implementation-workboard.md`.

Base currency is **CAD**. All persistent data lives in a local **SQLite**
database. Multiple fully-isolated profiles are supported with no login/PIN.

---

## Repository shape

```
TheBudget/
  apps/
    web/          React + TypeScript + Vite frontend (/app + prototype harness)
    api/          FastAPI backend (profiles/accounts; grows each stage)
  packages/       Shared UI/contracts packages (planned; not created yet)
  fixtures/
    statements/   Redacted/synthetic parser fixtures (never real statements)
  docs/
    architecture/ Architecture notes
    decisions/    Architecture Decision Records (ADRs)
    parser-notes/ Issuer parser findings
  scripts/
    start-local.sh / start-local.ps1   Convenience launchers
  tests/
    e2e/          End-to-end tests (future)
```

## Run the app — Python only, no Node.js required

The web UI is **pre-built and committed** (`apps/web/dist/`) and served by the
FastAPI backend, so you can run the whole app with just Python — one process,
one URL, no Node.js to install.

**Prerequisite:** Python 3.11+ only.

```bash
./scripts/start-app.sh          # macOS / Linux
```

```powershell
./scripts/start-app.ps1         # Windows PowerShell
```

That creates the virtualenv, installs backend dependencies, runs migrations,
starts the server on **http://127.0.0.1:8787**, and opens your browser. The app
and its local API are served together on that one address. Or do it by hand:

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
# then open http://127.0.0.1:8787
```

Everything below is only needed if you want to **develop the frontend** (which
does use Node as a build tool). Running the app does not.

---

## Developer prerequisites (frontend build only)

- **Node.js** 20+ (tested on 22) — only to rebuild the UI; not needed to run it
- **Python** 3.11+ (plan targets 3.12/3.13; 3.11 runs the current backend here)

> After changing anything under `apps/web/`, rebuild the committed UI with
> `cd apps/web && npm run build` so the Python-served app reflects your changes.

## Quick start (frontend dev server)

```bash
cd apps/web
npm install
npm run dev
```

Then open the printed local URL:

- **`/app`** — the **production application** (Meridian design): profile
  switching + management and per-profile account management, backed by the local
  API. Falls back to a friendly "create your first profile" flow.
- **`/`** — the prototype comparison harness: the four UI directions
  (**Meridian** ✓ selected, plus Aurora, Ledger, Horizon references) rendering
  the same Dashboard, Transactions, and Review Categories screens on a synthetic
  dataset, in light and dark. Retained for reference until later slices land.

The production `/app` screens need the backend running (see below) to load and
persist data; start both together with `./scripts/start-local.sh`.

To produce a static build / run checks:

```bash
npm run typecheck
npm test            # Vitest (jsdom) — API client + request-state tests
npm run build
```

## Run the full local development stack

After installing both frontend and backend dependencies, start the API and web
development servers together from any directory:

```bash
./scripts/start-local.sh          # macOS / Linux
```

```powershell
./scripts/start-local.ps1         # Windows PowerShell
```

Both services bind to loopback by default. See [`scripts/README.md`](scripts/README.md)
for setup checks, ports, and optional environment overrides.

## Backend (FastAPI + SQLite + Alembic)

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head          # create/upgrade the local SQLite schema
uvicorn app.main:app --host 127.0.0.1 --port 8787
python -m pytest -q           # backend tests
ruff check app tests alembic  # lint
```

The API binds to `127.0.0.1` (local-only) by design and currently exposes:

- `GET /health`
- Profiles: `GET/POST /profiles`, `GET/PATCH /profiles/{id}`,
  `POST /profiles/{id}/archive|restore`
- Accounts (scoped to a profile): `GET/POST /profiles/{id}/accounts`,
  `GET/PATCH /profiles/{id}/accounts/{accountId}`,
  `POST /profiles/{id}/accounts/{accountId}/archive|restore`
- Categories (scoped to a profile; 13 defaults seeded on profile creation):
  `GET/POST /profiles/{id}/categories`,
  `GET/PATCH /profiles/{id}/categories/{categoryId}`,
  `POST /profiles/{id}/categories/{categoryId}/archive|restore`

Every profile-scoped query is filtered by profile id in the service layer, so
cross-profile access returns 404 (never leaks existence). Money is stored as
integer cents. The database path is configurable via `ST_DATABASE_PATH` (default
`data/spending_tracker.db`); `*.db` is gitignored. Profiles/accounts support
**archive/restore**, not hard delete (safer; deletion-with-export is a later
deliberate step). See [`apps/api/README.md`](apps/api/README.md) for details.

## Design direction

Stage 1 built four comparable UI directions on identical synthetic data; the
product owner selected **Meridian** (Ledger's density + Horizon's warmth) as the
production design. Aurora, Ledger, and Horizon remain in the repo as references.
See `docs/decisions/0002-ui-directions.md`.

## Privacy & safety posture

- Server binds to `127.0.0.1` by default.
- No real credit-card statements are committed to this repository.
- Uploaded statement PDFs (future) are processed in a temp dir and deleted after
  import; raw bytes / full extracted text are never persisted.

See `SPENDING_TRACKER_PRODUCT_PLAN.md` (if present) for the full product plan.
