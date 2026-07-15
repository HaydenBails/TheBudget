# 1. Technology stack

- **Status:** Accepted
- **Date:** 2026-07-15

## Context

We are building a desktop-first, **local-first** personal spending tracker that
imports text-based credit-card statements, normalizes them into transactions,
categorizes spending, and produces insights. Design constraints from the product
plan (§16.2):

- Single user, running entirely on their own machine — no cloud, no accounts.
- All persistent data stays local and private; statements are sensitive.
- Desktop-first UI with dense data tables and charts.
- Small team / solo maintainer — favour mainstream, well-documented tooling with
  strong typing on both ends.
- The domain is money: correctness and reproducibility matter more than scale.

## Decision

Adopt the following stack:

**Frontend** — React + TypeScript + Vite; TanStack Query (server state),
TanStack Table (transaction grids), Recharts (charts), React Router (routing).

**Backend** — FastAPI (typed HTTP + OpenAPI), pydantic v2 / pydantic-settings
(models + config), SQLAlchemy 2.0 + Alembic (ORM + migrations), SQLite in WAL
mode (single-file local store), pdfplumber (text extraction from text-based
statement PDFs).

**Structure** — a monorepo with independently managed `apps/web` and `apps/api`,
plus `fixtures/`, `docs/`, `scripts/`, and `tests/e2e`. Shared `packages/*` are
deferred until a concrete cross-application contract or UI package is needed.

### Why these choices

- **FastAPI + pydantic v2** — first-class typing, request/response validation,
  and automatic OpenAPI docs; pairs naturally with a TypeScript frontend and a
  future shared `contracts` package.
- **SQLite (WAL)** — zero-config, single-file database that is trivially
  local-first and portable; WAL gives concurrent reads during import writes.
  A personal dataset never approaches SQLite's limits.
- **SQLAlchemy 2.0 + Alembic** — typed ORM with a proven migration story so the
  schema can evolve safely across stages.
- **pdfplumber** — reliable text/table extraction for text-based statements
  (scanned/image statements are explicitly out of scope).
- **React + TS + Vite** — fast iteration, huge ecosystem, strong typing.
- **TanStack Query/Table + Recharts** — mature, composable primitives for the
  data-dense, chart-heavy screens this product needs.

## Consequences

- **Positive:** end-to-end type safety; local-first and private by default;
  minimal operational surface (one process + one file DB); fast onboarding on
  mainstream tools; clean path to a shared API-contract package.
- **Negative / trade-offs:** SQLite is unsuitable for multi-user server
  deployment (acceptable — out of scope); pdfplumber cannot read scanned PDFs
  (documented limitation); two runtimes (Node + Python) must both be installed
  for local development (mitigated by `scripts/start-local.*`).
- Stage 0 ships only a FastAPI placeholder (`/`, `/health`); ORM, migrations,
  and parsing arrive in later stages.
- Node and Python dependencies remain app-local (`apps/web/package-lock.json`
  and `apps/api/requirements*.txt`). A root JavaScript workspace is intentionally
  deferred while there are no shared packages to coordinate.
- `scripts/start-local.sh` and `scripts/start-local.ps1` are development
  orchestration only: they preflight installed dependencies, bind both services
  to loopback by default, enable backend reload, and stop the pair when either
  child exits. They do not install dependencies or provide production packaging.
- CI is the Stage 0 acceptance gate: a clean checkout must pass frontend
  typechecking/build plus backend Ruff checks/tests. These checks are
  fail-closed; missing dependencies, tests, or lint failures are not tolerated.
