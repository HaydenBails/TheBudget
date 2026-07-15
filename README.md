# Spending Tracker (working title)

A polished, desktop-first, **local-first** personal spending tracker. It imports
text-based credit-card statements, normalizes them into transactions, suggests
categories, learns from your corrections, detects recurring charges, and turns
raw statement data into clear spending and savings insights.

> **Status:** Stage 0–1 in progress — repository scaffold + three interactive UI
> design directions on synthetic data. No real statement parsing or production
> dashboard services are wired up yet (by design — see the product plan).

Base currency is **CAD**. All persistent data lives in a local **SQLite**
database. Multiple fully-isolated profiles are supported with no login/PIN.

---

## Repository shape

```
TheBudget/
  apps/
    web/          React + TypeScript + Vite frontend (UI directions live here)
    api/          FastAPI backend (Stage 0 placeholder)
  packages/
    ui/           Shared design-system tokens/components (future)
    contracts/    Shared API types/schema (future)
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

## Prerequisites

- **Node.js** 20+ (tested on 22)
- **Python** 3.11+ (plan targets 3.12/3.13; 3.11 works for the Stage 0 placeholder)

## Quick start (frontend UI directions)

```bash
cd apps/web
npm install
npm run dev
```

Then open the printed local URL. The landing page lets you compare the three
interactive UI directions (**Aurora**, **Ledger**, **Horizon**), each with the
same Dashboard, Transactions, and Review Categories screens driven by the same
synthetic dataset, in both light and dark mode.

To produce a static build:

```bash
npm run build && npm run preview
```

## Backend placeholder

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

The API currently exposes only `/health` and binds to `127.0.0.1` (local-only)
by design. Domain models, migrations, and parsing arrive in later stages.

## Design directions

Stage 1 deliberately builds **three comparable UI directions** on identical
synthetic data so one can be selected before production components are built. See
`docs/decisions/0002-ui-directions.md`.

## Privacy & safety posture

- Server binds to `127.0.0.1` by default.
- No real credit-card statements are committed to this repository.
- Uploaded statement PDFs (future) are processed in a temp dir and deleted after
  import; raw bytes / full extracted text are never persisted.

See `SPENDING_TRACKER_PRODUCT_PLAN.md` (if present) for the full product plan.
