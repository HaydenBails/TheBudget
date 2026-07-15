# CLAUDE.md — guidance for Claude Code in this repo

This file orients Claude Code (and other AI agents) working in TheBudget. It
**complements, and defers to, [`AGENTS.md`](AGENTS.md)** and the workboard.

## Read this first, every session

1. **[`docs/implementation-workboard.md`](docs/implementation-workboard.md) — in
   full.** It is the single source of truth for the current stage, task board,
   ownership, dependencies, file boundaries, verification, and progress log.
2. The referenced ADRs in [`docs/decisions/`](docs/decisions) and
   [`docs/architecture/overview.md`](docs/architecture/overview.md).
3. The product requirements in
   [`SPENDING_TRACKER_PRODUCT_PLAN.md`](SPENDING_TRACKER_PRODUCT_PLAN.md).

If the workboard and an accepted ADR disagree, the ADR wins.

## Mandatory task protocol (from AGENTS.md)

- Claim exactly **one** `READY` task whose dependencies are `DONE`; set it to
  `IN PROGRESS` with agent/date/scope in the progress log **before** editing.
- Implement only that task; don't silently expand scope.
- Run the task's required verification and record the exact result.
- Move the task to `DONE` / `NEEDS REVIEW` / `BLOCKED` and append a handoff entry
  before ending.
- Never overwrite another agent's in-progress work; preserve unrelated changes.

## Non-negotiable constraints

- **Local-first**: servers bind `127.0.0.1`. No auth/cloud without a new ADR.
- **Money is integer cents.** Never floating point for money.
- **Profile isolation**: every profile-scoped record and query is filtered by
  profile; cross-profile access returns not-found, never leaks existence.
- **No real statements / raw PDF bytes / full extracted text** committed or
  persisted.
- Accepted stack: SQLite, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, React,
  TypeScript, Vite, TanStack Query, TanStack Table, Recharts, React Router.
- **Production UI direction is Meridian.** Aurora/Ledger/Horizon are references,
  not production. Reuse Meridian tokens in `apps/web/src/styles/meridian-tokens.css`.

## Frontend design work

AGENTS.md requires the `ui-ux-pro-max` skill for any task that changes/reviews UI
structure, visual design, interaction, responsive behavior, accessibility, or
UX. If that skill is **not installed in the current environment**, record the
exception in the workboard and still perform its equivalent checks manually:
- Accessibility: semantic markup, labelled inputs, real `<button>`s, visible
  focus, WCAG-AA contrast, never colour alone (pair colour with icon/label).
- Interaction & keyboard: full keyboard navigation of nav and forms.
- Responsive: fluid layouts, no fixed desktop-only widths for tables/charts.
- Theme: light **and** dark via `:root[data-theme='…']`.
- Reduced motion: respect `prefers-reduced-motion` for non-essential animation.

## graphify

A knowledge graph exists at `graphify-out/` for token-efficient navigation. If
the `graphify` CLI is installed, query it before broad repo reads
(`graphify query "<terms>" --budget 1000`) and run `graphify update .` after
code changes. If the CLI is **not installed**, note it and navigate via the
workboard + targeted search; do not present stale graph edges as current.

## Running things locally

Frontend (prototypes + production app):
```bash
cd apps/web && npm install && npm run dev      # http://127.0.0.1:5173
npm run typecheck && npm run build             # CI-equivalent checks
```
Backend (FastAPI + SQLite, local-only):
```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8787
python -m pytest -q                            # backend tests
```
Full stack together: `./scripts/start-local.sh` (or `.ps1` on Windows).

Pinned Pydantic v2 needs Python 3.12/3.13 (3.11 works for most; some pins may
require 3.12+). The DB lives at a configurable local path (`ST_DATABASE_PATH`);
`*.db` is gitignored.

## Branch / commit conventions

- Work on the designated feature branch; keep `main` updated via the same
  commits when asked. Do not push to `main` directly without explicit approval.
- End commit messages with the repo's Co-Authored-By/Claude-Session trailers.
- Do not commit `node_modules/`, `.venv/`, `*.db`, or build output.
