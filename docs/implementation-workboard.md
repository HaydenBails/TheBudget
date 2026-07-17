# Implementation workboard

- **Purpose:** Single source of truth for implementation planning and AI handoffs
- **Current phase:** Stage 3 import API + Meridian production UI (BE-16/FE-MERIDIAN-01)
- **Production UI direction:** Meridian, approved by the product owner
- **Last updated:** 2026-07-16

This document is intentionally operational. Product requirements remain in
[`SPENDING_TRACKER_PRODUCT_PLAN.md`](../SPENDING_TRACKER_PRODUCT_PLAN.md), while
architecture decisions remain in [`docs/decisions`](decisions). If this board
and an accepted ADR disagree, the ADR wins and this board must be corrected.

## Mandatory agent protocol

Every AI or human contributor must follow this sequence before making changes:

1. Read this document in full, including the progress log and blockers.
2. Read the linked ADRs and files listed under the intended task.
3. Check `git status` and preserve unrelated or pre-existing changes.
4. For any task that changes or reviews frontend UI structure, visual design,
   interactions, responsive behavior, accessibility, or UX, read and use the
   `ui-ux-pro-max` skill before making design decisions or changing UI files.
   Follow its applicable design-system/search workflow and include its
   accessibility, interaction, responsive, theme, and reduced-motion checks in
   the task verification record.
5. Select a task whose status is `READY` and whose dependencies are `DONE`.
6. Claim it by changing its status to `IN PROGRESS` and recording the agent,
   date, and intended file scope in the progress log.
7. Implement only that task. If scope must expand, record why before proceeding.
8. Run the task's required verification and record the exact result.
9. Change the task to `DONE`, `BLOCKED`, or `NEEDS REVIEW` and append a handoff
   entry before ending the session.

An agent must not claim more than one implementation task at a time. Research or
review tasks may run beside implementation only when they do not edit overlapping
files. Never overwrite another agent's in-progress work.

### Status definitions

| Status | Meaning |
| --- | --- |
| `BLOCKED` | A dependency, decision, or required external input is missing. |
| `READY` | Dependencies are complete and an agent may claim the task. |
| `IN PROGRESS` | Exactly one named agent owns the task. |
| `NEEDS REVIEW` | Implementation is complete but acceptance or review remains. |
| `DONE` | Acceptance criteria and verification are complete. |

### Progress-entry template

Append entries; do not rewrite another contributor's history.

```md
### YYYY-MM-DD HH:MM TZ — TASK-ID — Agent/tool name

- Status: IN PROGRESS | NEEDS REVIEW | DONE | BLOCKED
- Scope: files or directories this agent intends to touch
- Work: concise description of changes or investigation
- Verification: commands run and results, or "not run" with reason
- Decisions: choices made that affect later tasks
- Blockers/risks: none, or a concrete description
- Handoff: exact next action for the next agent
```

## Non-negotiable constraints

- The application remains local-first and binds to `127.0.0.1` by default.
- No authentication or cloud service is introduced without a new ADR.
- Money is stored and calculated as integer cents; never use floating point.
- Every persisted domain record is scoped to a profile where applicable.
- Real statements, raw PDF bytes, and full extracted statement text must not be
  committed or persisted.
- SQLite, FastAPI, SQLAlchemy 2, Alembic, React, TypeScript, Vite, TanStack Query,
  TanStack Table, Recharts, and React Router are the accepted stack.
- Meridian is the production UI direction. The Stage-1 comparison harness and
  every old prototype/runtime sample-data path, including the retired Meridian
  prototype, remain removed; production uses live API data only.

Read before implementation:

- [`0001-tech-stack.md`](decisions/0001-tech-stack.md)
- [`0002-ui-directions.md`](decisions/0002-ui-directions.md)
- [`0003-money-and-accounting.md`](decisions/0003-money-and-accounting.md)
- [`architecture/overview.md`](architecture/overview.md)

## Milestones

| Milestone | Exit condition | Status |
| --- | --- | --- |
| M0 — Stage 1 closure | Meridian is signed off and ADR 0002 records the final decision. | `DONE` |
| M1 — Development foundation | Database, migrations, app shell, API client, and test foundations work. | `DONE` |
| M2 — Profiles and accounts | A user can create/switch profiles and manage isolated accounts. | `DONE` (validated by QA-01; DOC-01 remains) |
| M3 — Core ledger schema | Categories and transactions persist with exact money semantics. | `DONE` |
| M4 — First production workspace | Production shell displays API-backed profile/account/category/transaction data reliably. | `DONE` |
| M5 — TD statement import | A TD PDF can be safely staged, reconciled, previewed, deduplicated, and atomically committed without retaining raw statement content. | `IN PROGRESS` |

## Dependency map

```text
S1-01
  ├── BE-01 ── BE-02 ── BE-03 ── BE-04 ── BE-05
  │                                  └────── BE-06
  └── FE-01 ── FE-02 ── FE-03 ── FE-04 ── FE-05
                                      │         │
                                      └── INT-01 ┘
BE-05 + BE-06 + FE-05 + INT-01 ── QA-01 ── DOC-01

QA-03
  ├── BE-12 ────────────────────────┐
  └── BE-13 ── BE-14 ──────────────┤
                                     └── BE-15 ── BE-16 ── FE-08 ── QA-04
```

Tasks with separate file scopes may run in parallel after their dependencies
are complete. Backend and frontend tasks should not share files except during
the explicitly named integration tasks.

## Task board

### Stage 1 closure

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| S1-01 | Obtain final Meridian sign-off and update ADR 0002 from pending to final. Record any requested visual changes as separate tasks. | — | `docs/decisions/0002-ui-directions.md` | Product owner explicitly approves Meridian; ADR status and consequences match that decision. | `DONE` | Product owner |

### Backend foundation

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-01 | Add SQLAlchemy 2 and Alembic dependencies and establish database configuration. | S1-01 | `apps/api/requirements*.txt`, `apps/api/app/config.py`, `apps/api/app/db/` | SQLite path is configurable and local; engine/session tests pass; existing health tests pass; Ruff passes. | `DONE` | Codex BE-01 agent |
| BE-02 | Initialize Alembic and create a reliable migration workflow. | BE-01 | `apps/api/alembic.ini`, `apps/api/alembic/`, API docs | Upgrade from an empty database succeeds; downgrade/upgrade cycle succeeds; commands are documented. | `DONE` | Codex / be02_alembic |
| BE-03 | Implement Profile and Account ORM models plus schemas. | BE-02 | `apps/api/app/models/`, `apps/api/app/schemas/`, migration versions | Foreign keys and delete behavior are explicit; identifiers and timestamps serialize correctly; migration applies cleanly. | `DONE` | Codex / be03_models |
| BE-04 | Implement profile/account repositories or services with enforced profile isolation. | BE-03 | `apps/api/app/services/`, backend unit tests | Cross-profile reads and writes are rejected or return no data; deletion behavior is tested. | `DONE` | Codex / be04_services |
| BE-05 | Add typed profile and account API routes. | BE-04 | `apps/api/app/routers/`, `apps/api/app/main.py`, API tests | CRUD happy paths, validation failures, missing resources, and isolation tests pass; OpenAPI contains routes. | `DONE` | Codex / be05_api_routes |
| BE-06 | Add integer-money and date utilities for later domain models. | BE-01 | `apps/api/app/domain/`, backend unit tests | Currency parsing rejects ambiguous/invalid input; cent arithmetic and date serialization tests pass; no float-based APIs. | `DONE` | Codex / be06_money_dates |

### Frontend foundation

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| FE-01 | Extract Meridian design tokens without changing prototype behavior. | S1-01 | `apps/web/src/styles/`, Meridian CSS, frontend tests | Colors, spacing, typography, radii, shadows, and light/dark tokens are centralized; build and visual smoke check pass. | `DONE` | Codex / fe01_meridian_tokens; acceptance by Claude Opus 4.8 |
| FE-02 | Create production application shell and routes separate from the comparison harness. | FE-01 | `apps/web/src/app/`, `apps/web/src/main.tsx`, reusable components | Production routes render Meridian navigation and theme; prototype routes remain accessible for reference; keyboard navigation works. | `DONE` | Claude Opus 4.8 |
| FE-03 | Install/configure TanStack Query and define the typed local API client/error model. | FE-02 | `apps/web/package*.json`, `apps/web/src/api/`, query client | Lockfile is consistent; health request works; loading/error states are tested; API base defaults to loopback/local configuration. | `DONE` | Claude Opus 4.8 |
| FE-04 | Build profile switcher and profile management UI. | FE-03, BE-05 | `apps/web/src/features/profiles/` | List/create/select/delete flows work against API; destructive action confirms; loading, empty, and error states exist. | `DONE` | Claude Opus 4.8 |
| FE-05 | Build account management UI for the active profile. | FE-04, BE-05 | `apps/web/src/features/accounts/` | Account list/create/edit/delete stays scoped to active profile; form validation and empty/error states are covered. | `DONE` | Claude Opus 4.8 |

### Integration, quality, and documentation

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| INT-01 | Add isolated integration-test database and frontend API mocking/test harness. | BE-05, FE-03 | API test fixtures, web test configuration | Tests never touch the user's real database; backend API tests and frontend request-state tests run deterministically. | `DONE` | Claude Opus 4.8 |
| QA-01 | Validate the complete profiles/accounts vertical slice. | BE-05, BE-06, FE-05, INT-01 | Cross-app review; avoid feature edits unless defects are found | Clean setup, migrations, backend tests/lint, frontend typecheck/build/tests, loopback startup, keyboard smoke test, and profile-isolation scenarios pass. | `DONE` | Claude Opus 4.8 |
| DOC-01 | Update setup, architecture, API, and user-flow documentation after the slice lands. | QA-01 | `README.md`, `docs/architecture/`, `apps/api/README.md` | A new developer can reproduce setup and the documented behavior matches verified commands. | `DONE` | Claude Opus 4.8 |

### Categories slice (Stage 2 continued → M3)

Expanded 2026-07-16 after the profiles/accounts slice passed QA. Same rigour:
profile isolation in the service layer, archive/restore (no hard delete), money
rules N/A here, and full verification before `DONE`.

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-07 | Category domain: ORM model, schemas, migration, profile-scoped services, and idempotent default-category seeding (auto-seeded on profile creation). | BE-03 | `apps/api/app/models/category.py`, `apps/api/app/schemas/category.py`, `apps/api/app/services/categories.py`, seed helper, `services/profiles.py` (seed hook), `models/__init__`, `schemas/__init__`, `services/__init__`, `alembic/versions/`, backend tests | Category is profile-scoped (FK + index) with slug/name/color/icon/parent/excluded/is_default/sort_order/archived; migration applies from the prior head and reverses; creating a profile seeds the 13 defaults idempotently; cross-profile reads/writes return not-found; archive/restore covered; pytest + ruff pass. | `DONE` | Claude Opus 4.8 |
| BE-08 | Typed category API routes nested under the owning profile. | BE-07 | `apps/api/app/routers/categories.py`, `apps/api/app/routers/__init__.py`, `apps/api/app/main.py`, API tests | `GET/POST /profiles/{id}/categories`, `GET/PATCH /profiles/{id}/categories/{categoryId}`, `POST .../archive|restore`; happy paths, field-specific 422s, missing/cross-profile 404, OpenAPI contains routes; pytest passes. | `DONE` | Claude Opus 4.8 |
| FE-06 | Category management UI for the active profile. | FE-05, BE-08 | `apps/web/src/features/categories/` | List seeded defaults + custom categories (grouped, sorted), create (name/colour/icon/excluded), edit, archive/restore — all scoped to the active profile; validation + empty/error states; keyboard + light/dark checks. | `DONE` | Claude Opus 4.8 |
| QA-02 | Validate the categories slice. | BE-08, FE-06 | Cross-app review; avoid feature edits unless defects are found | Migrations, backend tests/lint, frontend typecheck/test/build, seeding-on-create, and category profile-isolation scenarios pass. | `DONE` | Claude Opus 4.8 |

### Transactions slice (M3 → M-ledger)

Expanded 2026-07-16 after the categories slice passed QA. This is a larger slice;
it is split into schema → services → routes → UI. Money is integer cents and the
spending-inclusion policy follows `docs/decisions/0003-money-and-accounting.md`.
Split child amounts must sum to the parent amount. All rows are profile-scoped
and soft-deleted (restorable), never hard-deleted.

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-09 | Transaction/split/tag schema: ORM models, Pydantic schemas, migration, and a split-sum domain validator. | BE-07 | `apps/api/app/models/{transaction,transaction_split,tag}.py`, `schemas/transaction.py`, `services/transactions_rules.py` (split-sum + default inclusion), `models/__init__`, `schemas/__init__`, `alembic/versions/`, backend tests | Transaction is profile+account scoped (signed `amount_cents`, type/status/source enums, `included_in_spending`, nullable `category_id`, soft-delete `deleted_at`); split rows reference a category and sum-check against the parent; tags are unique per profile with a many-to-many link; migration applies/reverses from the prior head; split-sum + default-inclusion helpers unit-tested; pytest + ruff pass. | `DONE` | Claude Opus 4.8 |
| BE-10 | Transaction services: profile-scoped create/list/filter/update, split + tag management, soft delete/restore, spending-inclusion policy. | BE-09 | `apps/api/app/services/transactions.py`, backend tests | CRUD + filtering (account/category/type/date/included/search) scoped to profile; splits validated to sum to the parent; soft delete hides from default lists and metrics; cross-profile access → not-found; archive/restore-equivalent (soft delete) covered; pytest passes. | `DONE` | Codex / be10_transaction_services |
| BE-11 | Typed transaction API routes (incl. bulk categorize/exclude) nested under the profile. | BE-10 | `apps/api/app/routers/transactions.py`, `app/main.py`, API tests | List/create/get/patch/soft-delete/restore + a bulk endpoint; validation 422; missing/cross-profile 404; OpenAPI contains routes; pytest passes. | `DONE` | Codex / be11_contract_audit |
| FE-LEDGER-01 | Consolidate the production frontend onto Ledger and retire Stage-1 comparison/sample-data features. | FE-06 | `apps/web/src/App.tsx`, `apps/web/src/app/`, production styles/tokens, Stage-1 `directions/` + mock-data removal, frontend tests, `apps/web/dist/` | `/` and `/app/*` enter one Ledger-styled API-backed app; comparison switcher/routes and unused Aurora/Horizon/Meridian runtime code are removed; no production runtime imports synthetic `mockData`; every top-nav control works by keyboard and pointer; responsive/light/dark/reduced-motion checks pass; typecheck/test/build pass and committed `dist` is refreshed. | `DONE` | Codex / ledger_consolidation |
| FE-07 | Transactions workspace UI (TanStack Table) for the active profile. | FE-LEDGER-01, FE-06, BE-11 | `apps/web/src/features/transactions/` | Virtualized/paginated table scoped to the active profile: search + filters, inline category assignment, included/excluded display, soft delete + restore; loading/empty/error states; keyboard + light/dark checks. | `DONE` | Codex / be11_contract_audit |
| FE-MERIDIAN-01 | Supersede Ledger styling with Meridian across the API-backed production workspace while keeping prototypes and sample data retired. | FE-07 | `apps/web/src/app/`, current feature styles/copy, `apps/web/dist/`, ADR 0002, direction text in this workboard | `/` and `/app/*` retain the current real API flows under one Meridian token system and responsive shell; no comparison route, prototype runtime, or sample data returns. Top controls work by keyboard/pointer; visible focus, ≥44px targets, light/dark contrast, reduced motion, 375/768/1440 and 200%-zoom checks pass. Typecheck, Vitest, build, rendered QA, and committed-dist refresh pass. | `DONE` | Codex / ledger_consolidation; rendered acceptance by root |
| QA-03 | Validate the transactions slice. | BE-11, FE-07 | Cross-app review; avoid feature edits unless defects are found | Migrations, backend tests/lint, frontend typecheck/test/build, split-sum + inclusion rules, and transaction profile-isolation scenarios pass. | `DONE` | Codex / ledger_review |

### Stage 3 — Import framework and TD parser (M5)

Expanded 2026-07-16 after QA-03 validated the transaction workspace. BE-12 and
BE-13 have disjoint file ownership and may run in parallel. BE-12 exclusively
owns the import migration and persistence contracts; BE-13/BE-14 exclusively
own extraction, parser, reconciliation, and fixture files. BE-15 is the first
convergence point and the only task in this slice that writes staged rows into
final transaction tables.

All work remains local-only. Real statements, raw PDF bytes, full extracted
statement text, client filesystem paths, full account numbers, and transaction
lists in logs must never be committed or persisted. Temporary statement files
must use server-owned paths and be deleted after commit, cancellation, or any
failure. Only structured transaction candidates, statement metadata,
validation results, sanitized source filenames, parser versions, and
non-reversible fingerprints may persist.

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-12 | Import persistence and canonical staging contracts. | QA-03 | `apps/api/app/models/{import_batch,import_staged_transaction,import_warning,import_transaction_link}.py`; model/schema exports; profile/account/transaction relationships; `apps/api/app/schemas/imports.py`; migration `0006`; focused model/schema/migration tests | Profile-scoped batch and staging rows; selected account must belong to the profile; indexed file hash/logical statement key and profile/account transaction fingerprint; structured integer-cent summaries, validation status, parser/version, sanitized source filename, source-row reference, and duplicate decision. Add the transaction import FK and nullable original foreign amount/currency plus fixed-precision exchange rate. Migration applies/reverses from 0005. Schema inspection proves there is no PDF-byte, extracted-page-text, client-path, or full-account-number column. Pytest and Ruff pass. | `DONE` | Codex / be10_transaction_services |
| BE-13 | Safe document extraction, parser interface, reconciliation, and fingerprint primitives. | QA-03 | `apps/api/app/importing/{contracts,document,reconciliation,fingerprints,errors}.py`; `apps/api/app/parsers/base.py`; `apps/api/requirements.txt`; focused importing tests | Implement canonical `StatementParser.detect`, `extract_metadata`, `extract_transactions`, and `reconcile`; streamed SHA-256; extension/MIME/PDF-magic validation; configurable file/page limits; actionable rejection of scanned/image-only PDFs; server-owned temporary paths only; cleanup on success, exception, and cancellation; logs contain IDs/counts/deltas only. Money uses integer cents and exchange-rate parsing uses Decimal/fixed precision, never float. Pytest and Ruff pass. | `DONE` | Codex / be11_contract_audit |
| BE-14 | TD credit-card parser and privacy-safe regression fixture matrix. | BE-13 | `apps/api/app/parsers/td.py`; `fixtures/statements/td/**`; `docs/parser-notes/td.md`; TD parser tests | Synthetic/redacted fixtures plus expected canonical JSON and a manifest cover first/middle/last pages, page breaks, headers/footers/payment slips/legal text, comma amounts, negative credits/refunds, `PAYMENT - THANK YOU`, fees, interest, repeated legitimate rows, foreign-currency continuation lines, and unsupported layouts. Preserve transaction/posting dates and raw descriptions; charged CAD amount is integer cents; reconcile every available section within one cent. No real statement, name, address, barcode, or unmasked number is committed. | `DONE` | Codex / be11_contract_audit |
| BE-15 | Profile-isolated import preview, duplicate detection, and atomic commit services. | BE-12, BE-14, BE-10 | `apps/api/app/services/imports.py`; minimal import-aware extension to `apps/api/app/services/transactions.py`; service exports; focused import service tests | Preview persists canonical candidates/warnings without final transactions; suggests an account from issuer/masked digits but accepts only a same-profile account. Exact file/logical duplicates are blocked with the prior import reference; occurrence-aware fingerprints preserve legitimate identical purchases; only high-confidence overlaps auto-skip. Commit is atomic/idempotent, sets `pdf_import`, import FK, and source-row links; `needs_review` requires explicit acknowledgement. Failed commit leaves no partial transaction rows. Commit/cancel/failure cleans raw PDF and extracted text, and logs expose no statement content. | `DONE` | Codex / be10_transaction_services |
| BE-16 | Typed profile-nested import API. | BE-15 | `apps/api/app/routers/imports.py`; router exports; `apps/api/app/main.py`; upload-limit configuration; import API/OpenAPI tests | Add `POST /profiles/{profile_id}/imports/preview`, `GET /profiles/{profile_id}/imports/{import_id}`, `POST .../{import_id}/commit`, and `POST .../{import_id}/cancel`; Stage 3 accepts one TD PDF per preview. Responses contain only structured metadata, totals, warnings, and duplicate decisions. Test 413 oversize, 415 invalid media, readable 422 scanned/unsupported/reconciliation errors, 409 duplicate, uniform cross-profile 404, malicious filename handling, rollback, cleanup, and OpenAPI coverage. | `DONE` | Codex / be10_transaction_services |
| FE-08 | Meridian Import Statement workflow and working top action. | BE-16, FE-07 | `apps/web/src/features/imports/**`; minimal `apps/web/src/app/{AppShell.tsx,app.css}` route/action wiring; frontend API tests; `apps/web/dist/**` | The top Import button navigates to `/app/imports`; provide an accessible select/drop-PDF flow, account suggestion/selection, loading/error/cancel states, preview counts by type, expected-versus-parsed totals, warnings, skipped duplicates, explicit needs-review acknowledgement, and commit success linking to Transactions. File data remains transient browser state and is never placed in localStorage, IndexedDB, fixtures, or sample runtime data; clear it after cancel/commit. The agent must read and use `ui-ux-pro-max` and record pointer/keyboard/focus, ≥44px targets, light/dark contrast, reduced motion, 375/768/1440 layouts, and 200%-zoom checks. Typecheck, Vitest, build, and committed-dist refresh pass. | `DONE` | Codex / ledger_consolidation; rendered acceptance by root; independent review CLEAN |
| QA-04 | Validate the complete Stage 3 import framework and TD vertical slice. | BE-16, FE-08 | Cross-app validation only; avoid feature edits unless defects are found | Fresh migration cycle; Ruff/full pytest; frontend typecheck/test/build; loopback-only run; synthetic TD fixture matrix reconciles within one cent. Private supplied samples may run only from an ignored external path. Verify re-import creates zero duplicates, identical legitimate rows survive occurrence indexing, profile isolation, needs-review acknowledgement, malicious/oversize/scanned inputs, cancel/parser/database-failure cleanup, atomic rollback, log redaction, and absence of raw PDF/full extracted text in the database and temporary storage after terminal operations. Browser-test the complete Import-button workflow. | `IN PROGRESS` | Codex / be11_contract_audit |
| OPS-CLEAN-01 | Remove generated backend test artifacts accidentally retained in the API tree and prevent recurrence. | — | `apps/api/` generated test/cache directories; repository `.gitignore`; this workboard | Delete only disposable pytest/cache/database/key artifacts; preserve API source, tests, migrations, data, and `.venv`; add scoped ignore rules; verify no matching generated directories remain and tracked API files are limited to intentional source/project files. | `DONE` | Codex / root |

### Budgets slice (product plan §11)

Added 2026-07-17 after the rich Meridian dashboard landed with "Coming soon"
placeholders for Category budgets. This vertical slice implements monthly
budgets (overall + per category) end-to-end. File ownership is disjoint from
the in-flight QA-04 import validation: it adds a new `budget` model, schema,
service, router, migration `0007`, and a frontend `features/budgets/` feature
plus the dashboard budgets card. Money is integer cents; every row is
profile-scoped; uniqueness follows the plan's "one overall budget per
profile/month" and "one category budget per profile/category/month" rules.

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-BUDGET-01 | Budget domain + typed profile-nested budget API. | BE-08, BE-11 | `apps/api/app/models/budget.py`, `apps/api/app/schemas/budget.py`, `apps/api/app/services/budgets.py`, model/schema/service exports, `apps/api/app/routers/budgets.py`, `app/main.py`, `alembic/versions/0007_budget_models.py`, backend tests | Budget is profile-scoped with nullable `category_id` (NULL = overall), `period_month` (`YYYY-MM`), and positive `limit_cents`. Partial unique indexes enforce one overall budget per profile/month and one category budget per profile/category/month; a duplicate returns 409. A category budget's category must belong to the profile. List filters by month; cross-profile access returns not-found. Migration applies/reverses from 0006. Pytest + Ruff pass. | `DONE` | Claude Opus 4.8 |
| FE-BUDGET-01 | Budgets management UI + dashboard budgets card. | BE-BUDGET-01, FE-07 | `apps/web/src/features/budgets/`, `apps/web/src/app/{AppShell.tsx,pages.tsx,dashboard.css}`, `apps/web/dist/` | A Budgets page lists the active month's overall + per-category budgets, sets/edits/removes limits, and shows progress (amount + %) with 75/90/100% threshold states computed from live transactions. The dashboard "Category budgets" card shows real progress bars (top categories) and links to Budgets. Keyboard/focus, light/dark, and responsive checks pass; typecheck/build pass and committed `dist` is refreshed. | `DONE` | Claude Opus 4.8 |

### Amex parser slice (backlog item 1 — first half)

Claimed 2026-07-17 at the product owner's direct request to work on Amex
statement import, ahead of the QA-04 gate (recorded as an exception in the
progress log, like prior direct-request tasks). Scope is the **section-aware
Amex credit-card parser and privacy-safe synthetic fixtures**, plus a small
**parser resolver** so preview auto-detects the issuer (TD or Amex) instead of
hardcoding TD. Multi-file import and mixed-issuer *batching* remain future
work. File ownership is additive/disjoint: a new parser, new fixtures, a
resolver, and a one-line router swap; it does not change the TD parser or the
import persistence/services.

All privacy rules from Stage 3 apply: fixtures are entirely synthetic/redacted,
no real statement content, no full account numbers, integer cents only, and
exchange rates parsed as fixed-precision Decimal.

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-AMEX-01 | Section-aware Amex credit-card parser, synthetic fixture matrix, and issuer-detecting parser resolver. | BE-14, BE-16 | `apps/api/app/parsers/amex.py`, `apps/api/app/parsers/{__init__,resolver}.py`, `apps/api/app/routers/imports.py` (resolver swap), `fixtures/statements/amex/**`, `apps/api/tests/test_amex_parser.py`, `apps/api/tests/test_parser_resolver.py` | Amex parser implements `detect`/`extract_metadata`/`extract_transactions`/`reconcile`: recognises the AMEX issuer + a section-aware layout (Payments-and-Credits vs New-Charges), preserves transaction dates and raw descriptions, stores charged CAD as integer cents, handles payments/refunds/fees/interest and a foreign-currency continuation, and reconciles net + debit/credit sections within one cent. A resolver picks the matching parser by detection confidence; unknown issuers raise a readable unsupported error. Synthetic fixtures + expected canonical JSON + manifest cover the matrix; no real statement/number/address is committed. Pytest + Ruff pass. | `DONE` | Claude Opus 4.8 |

### Recurring charges slice (product plan §12)

Claimed 2026-07-17 at the product owner's direct request to keep building
features. Implements recurring-charge / subscription detection end-to-end
(product goal #3) and turns the dashboard's last "Coming soon" card real.
Additive/disjoint from QA-04: a new `recurring_series` model/service/router,
migration `0008`, a pure detection-rules module, and a frontend
`features/recurring/` feature plus the dashboard upcoming-recurring card. The
existing (already-present) nullable `transactions.recurring_series_id` column is
linked by the detection service.

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| BE-RECUR-01 | Recurring-series domain + deterministic detection + typed API. | BE-11 | `apps/api/app/services/recurring_rules.py`, `apps/api/app/models/recurring_series.py`, `apps/api/app/schemas/recurring.py`, `apps/api/app/services/recurring.py`, model/schema/service exports, `apps/api/app/routers/recurring.py`, `app/main.py`, `alembic/versions/0008_recurring_series.py`, backend tests | Detection is a pure, unit-tested function: groups included debit purchases by normalized merchant, recognises weekly/biweekly/monthly/quarterly/annual cadence with interval + amount tolerances, ignores irregular frequent merchants (groceries/dining), and assigns high/medium/low confidence (≥3 consistent = high, 2 = low). Series are profile-scoped with cadence, expected amount/range, next-expected date, confidence, rationale, status (keep/review/cancel/ended/ignored) and confirmed flag. `POST .../recurring/detect` syncs idempotently and links matched transactions; list/get/patch scoped to profile; cross-profile access not-found. Migration applies/reverses from 0007. Pytest + Ruff pass. | `DONE` | Claude Opus 4.8 |
| FE-RECUR-01 | Recurring-charges UI + dashboard upcoming-recurring card. | BE-RECUR-01, FE-07 | `apps/web/src/features/recurring/`, `apps/web/src/app/{AppShell.tsx,pages.tsx,dashboard.css}`, `apps/web/dist/` | A Recurring page runs detection, lists detected series with cadence, monthly + annualized cost, next-expected date, confidence, and a keep/review/cancel + confirm workflow. The dashboard "Upcoming recurring" card shows the next expected charges (real data) and links to the page. Keyboard/focus, light/dark, responsive checks pass; typecheck/build pass and committed `dist` refreshed. | `DONE` | Claude Opus 4.8 |

## Later-stage backlog

Do not claim these until M5 passes QA-04 and the board has been expanded with
equivalent dependencies, file ownership, privacy criteria, and verification.

1. Amex parser: **section-aware parser claimed as BE-AMEX-01 (2026-07-17)**;
   multi-file import and mixed-issuer batching remain.
2. CIBC discovery gate and parser after representative private samples exist.
3. Categorization, merchant normalization, and remembered rules.

## Known blockers and decisions needed

| ID | Item | Owner | Resolution needed |
| --- | --- | --- | --- |
| D-01 | Meridian is selected but ADR 0002 still says final sign-off is pending. | Product owner | `RESOLVED` — Meridian approved as-is on 2026-07-15 and ADR 0002 updated. |
| D-02 | Production prototype retention/removal timing is not explicit. | Product owner/lead agent | `RESOLVED` — the 2026-07-16 latest decision selects Meridian styling while keeping the comparison harness, every prototype route, and sample runtime data retired. |

## Progress log

### 2026-07-15 — PLAN-01 — Codex

- Status: `DONE`
- Scope: `AGENTS.md`, `docs/implementation-workboard.md`
- Work: Established the mandatory agent protocol, dependency-ordered Stage 2
  plan, task ownership/status board, acceptance criteria, blockers, and handoff
  format.
- Verification: Documentation links and task dependencies reviewed manually;
  repository formatting check to be recorded with the creating change.
- Decisions: Meridian sign-off is a hard gate before production implementation.
  The first production slice is profiles and accounts.
- Blockers/risks: D-01 requires product-owner confirmation.
- Handoff: Product owner resolves D-01; the next agent updates S1-01, then claims
  either BE-01 or FE-01.

### 2026-07-15 — S1-01 — Product owner / Codex

- Status: `DONE`
- Scope: `docs/decisions/0002-ui-directions.md`, this workboard
- Work: Product owner approved Meridian as the production UI direction; removed
  the pending-sign-off status and unlocked the first backend/frontend tasks.
- Verification: ADR and workboard status reviewed for consistency.
- Decisions: Meridian is approved as-is. Reference prototypes remain available
  until the first production vertical slice passes QA.
- Blockers/risks: none
- Handoff: Two agents may claim BE-01 and FE-01 in parallel.

### 2026-07-15 14:42 EDT — FE-01 — Codex / fe01_meridian_tokens

- Status: `IN PROGRESS`
- Scope: `apps/web/src/styles/`, `apps/web/src/directions/meridian/meridian.css`,
  `apps/web/src/directions/meridian/index.tsx`, this workboard
- Work: Centralize Meridian color, spacing, typography, radius, shadow, and
  light/dark theme tokens without changing prototype behavior.
- Verification: pending implementation
- Decisions: Keep tokens app-local under `apps/web/src/styles/`; shared packages
  remain deferred per ADR 0001.
- Blockers/risks: none
- Handoff: Complete token extraction, build, and visual smoke checks.

### 2026-07-15 14:50 EDT — FE-01 — Codex / fe01_meridian_tokens

- Status: `NEEDS REVIEW`
- Scope: `apps/web/src/styles/meridian-tokens.css`,
  `apps/web/src/directions/meridian/meridian.css`,
  `apps/web/src/directions/meridian/index.tsx`, this workboard
- Work: Extracted Meridian typography, spacing, shape, elevation, semantic
  color, and light/dark theme tokens into an app-local stylesheet. Retained the
  prototype's existing semantic variable names as aliases and replaced selected
  literal typography/spacing values with equivalent tokens.
- Verification: `git diff --check` passed (line-ending warnings only). Static
  token/reference inspection passed. `npm run build` could not run because
  Node/npm are not installed or available on PATH; the visual smoke check was
  therefore also unavailable.
- Decisions: Tokens are scoped under `.mrd` to avoid changing Aurora, Ledger,
  Horizon, or harness styling. Existing values and CSS selector specificity are
  preserved.
- Blockers/risks: Build and light/dark visual acceptance remain unverified in
  this environment due to the missing Node toolchain.
- Handoff: On a machine with Node/npm, run `npm run build` in `apps/web`, then
  smoke-check `/meridian/dashboard`, `/meridian/transactions`, and
  `/meridian/review` in both themes. Mark FE-01 `DONE` if unchanged; only then
  unblock FE-02.

### 2026-07-15 — BE-01 — Codex BE-01 agent

- Status: `IN PROGRESS`
- Scope: `apps/api/requirements*.txt`, `apps/api/app/config.py`,
  `apps/api/app/db/`, and database-focused backend tests
- Work: Claiming the configurable local SQLite engine/session foundation with
  SQLAlchemy 2, Alembic dependencies, and WAL behavior.
- Verification: not run; implementation has not started
- Decisions: Keep database construction side-effect free and injectable so
  tests can use isolated temporary SQLite files.
- Blockers/risks: none
- Handoff: Complete BE-01 acceptance checks, then unblock BE-02 and BE-06.

### 2026-07-15 — BE-01 — Codex BE-01 agent

- Status: `DONE`
- Scope: `apps/api/requirements.txt`, `apps/api/.env.example`,
  `apps/api/app/config.py`, `apps/api/app/db/`, `apps/api/tests/test_database.py`
- Work: Added pinned SQLAlchemy 2 and Alembic runtime dependencies, a
  configurable local SQLite path, explicit injectable engine/session factories,
  automatic database-directory creation, WAL mode, foreign-key enforcement,
  and isolated configuration/engine/session tests.
- Verification: `.venv\\Scripts\\python -m pytest -q --basetemp .test-tmp
  -p no:cacheprovider` — 5 passed; `.venv\\Scripts\\python -m ruff check app
  tests` — all checks passed; `git diff --check` — passed.
- Decisions: Database engines are constructed explicitly rather than at import
  time, allowing later services and tests to inject isolated database files.
- Blockers/risks: The machine defaulted to unsupported Python 3.14 for the pinned
  Pydantic version, so verification used a uv-provisioned Python 3.13 virtualenv.
- Handoff: BE-02 and BE-06 are now ready; BE-02 should consume these factories
  when wiring Alembic without changing their public contract unnecessarily.

### 2026-07-15 15:05 EDT — FE-01 — Codex / fe01_acceptance_review

- Status: `NEEDS REVIEW`
- Scope: read-only review of `apps/web/src/styles/meridian-tokens.css`,
  `apps/web/src/directions/meridian/meridian.css`, and
  `apps/web/src/directions/meridian/index.tsx`; this workboard only
- Work: Independently reviewed FE-01 token completeness, `.mrd` scoping,
  backwards-compatible aliases, import order, CSS structure, and the exact
  prototype diff. No implementation defect was found: all 23 Meridian custom
  properties referenced by `meridian.css` are defined, light values match the
  removed declarations, dark overrides match the removed declarations, and
  token selectors remain scoped to Meridian.
- Verification: `git diff -- apps/web/src/directions/meridian/index.tsx
  apps/web/src/directions/meridian/meridian.css
  apps/web/src/styles/meridian-tokens.css` reviewed; static custom-property
  comparison reported 46 definitions, 23 references, and zero undefined
  references; brace checks reported `meridian.css` 156/156 and token CSS 2/2.
  `Get-Command` checks for Node, npm, npx, pnpm, Yarn, Bun, and Deno plus common
  nvm/fnm/Volta/Scoop locations found no usable JavaScript runtime. Build and
  visual smoke checks therefore could not run.
- Decisions: Keep FE-01 at `NEEDS REVIEW`; static evidence is clean, but its
  explicit build and light/dark visual acceptance criteria are not yet met.
- Blockers/risks: Missing local Node toolchain prevents runtime acceptance.
- Handoff: Run `npm run build` in `apps/web` and visually smoke-check Meridian's
  dashboard, transactions, and review screens in light and dark themes on a
  Node-enabled machine. Mark FE-01 `DONE` and unblock FE-02 only if those pass.

### 2026-07-15 15:20 EDT — BE-06 — Codex / be06_money_dates

- Status: `IN PROGRESS`
- Scope: `apps/api/app/domain/`, `apps/api/tests/test_money.py`,
  `apps/api/tests/test_dates.py`, this workboard
- Work: Claiming exact integer-cent parsing/arithmetic and unambiguous ISO date
  serialization utilities for later domain models.
- Verification: pending implementation
- Decisions: Public money APIs accept integer cents or strict decimal strings,
  never floating-point values; dates use strict ISO 8601 calendar dates.
- Blockers/risks: none
- Handoff: Implement focused utilities/tests, run pytest and Ruff, then record
  final acceptance results.

### 2026-07-15 15:28 EDT — BE-06 — Codex / be06_money_dates

- Status: `DONE`
- Scope: `apps/api/app/domain/`, `apps/api/tests/test_money.py`,
  `apps/api/tests/test_dates.py`, this workboard
- Work: Added strict decimal-text-to-cent parsing, exact cent addition/summing,
  and strict ISO calendar-date parsing/serialization with focused rejection
  coverage for floats, booleans, locale/currency notation, invalid dates, and
  datetime values.
- Verification: `.venv\Scripts\python -m pytest -q tests/test_health.py
  tests/test_money.py tests/test_dates.py -p no:cacheprovider` — 33 passed;
  `.venv\Scripts\python -m ruff check app tests` — all checks passed;
  `git diff --check` — passed (line-ending warnings only). A full-suite attempt
  reached 33 passing tests but the three database tests and pytest cleanup hit
  sandbox `PermissionError` on their temporary directories.
- Decisions: Parsing accepts canonical plain decimal strings with zero to two
  fraction digits; leading zeroes, grouping separators, symbols, whitespace,
  exponent notation, and non-string inputs are rejected rather than inferred.
- Blockers/risks: none for BE-06; the existing database-test temporary-directory
  permission behavior should be rechecked outside this sandbox.
- Handoff: Later transaction/schema work may import these primitives from
  `app.domain`; preserve the integer-only arithmetic and strict boundary rules.

### 2026-07-15 — BE-02 — Codex / be02_alembic

- Status: `IN PROGRESS`
- Scope: `apps/api/alembic.ini`, `apps/api/alembic/`, `apps/api/README.md`, this workboard
- Work: Initialize Alembic around the configurable local SQLite database and document a reliable migration workflow.
- Verification: pending implementation
- Decisions: Reuse BE-01 settings and engine factory; do not introduce domain models or a schema revision in BE-02.
- Blockers/risks: none
- Handoff: Verify upgrade from empty and downgrade/upgrade, then unblock BE-03.

### 2026-07-15 — BE-02 — Codex / be02_alembic

- Status: `DONE`
- Scope: `apps/api/alembic.ini`, `apps/api/alembic/`, `apps/api/README.md`, this workboard
- Work: Added a project-local Alembic environment wired to BE-01's configurable settings and engine factory, an empty migration baseline, a typed revision template, and cross-platform migration commands.
- Verification: With `ST_DATABASE_PATH=.test-tmp/be02-migrations.db`, `.venv\Scripts\python -m alembic upgrade head`, `current`, `downgrade base`, and `upgrade head` all passed; `.venv\Scripts\python -m pytest -q --basetemp .test-tmp/pytest -p no:cacheprovider` passed (36 tests); `.venv\Scripts\python -m ruff check app tests alembic` passed; `git diff --check` passed with line-ending warnings only.
- Decisions: The baseline creates no domain tables. BE-03 owns declarative metadata wiring and the first schema migration; SQLite batch rendering is enabled for future compatible alterations.
- Blockers/risks: none
- Handoff: BE-03 is `READY`; import its declarative metadata into `alembic/env.py` before generating the Profile/Account revision.

### 2026-07-15 15:03 EDT — BE-03 — Codex / be03_models

- Status: `IN PROGRESS`
- Scope: `apps/api/app/models/`, `apps/api/app/schemas/`,
  `apps/api/alembic/versions/`, focused BE-03 tests, Alembic metadata wiring,
  and this workboard
- Work: Claiming Profile and Account SQLAlchemy 2 models, Pydantic schemas, and
  the first domain migration with explicit ownership and delete semantics.
- Verification: pending implementation
- Decisions: Preserve BE-01/BE-02 public database contracts and do not enter
  BE-04 repository/service scope.
- Blockers/risks: none
- Handoff: Implement the scoped models/schemas/migration, run focused and
  required backend verification, then record acceptance results.

### 2026-07-15 15:06 EDT — FE-01 — Codex / fe01_acceptance

- Status: `NEEDS REVIEW`
- Scope: read-only acceptance review of `apps/web/src/styles/meridian-tokens.css`,
  `apps/web/src/directions/meridian/meridian.css`, and
  `apps/web/src/directions/meridian/index.tsx`; this workboard only
- Work: Re-reviewed the FE-01 diff for selector, cascade, import-order, and
  token-reference regressions. Located a cached Node 24.14.0 runtime and pnpm
  runner outside `PATH`, but the workspace has no installed frontend
  dependencies; no software was installed. The in-app browser reported no
  available browser target, so a rendered smoke check could not be performed.
- Verification: Resolved-value comparison checked all 35 original Meridian
  light/dark custom-property declarations against the extracted tokens with
  zero mismatches; static inspection found 46 unique token definitions, 23
  stylesheet references, zero undefined references, and balanced braces in
  both CSS files. `git diff --check` passed with line-ending warnings only.
  An explicit cached-runtime build attempt stopped before project execution
  because TypeScript/Vite dependencies are absent; build and visual smoke
  checks remain unverified.
- Decisions: Keep FE-01 at `NEEDS REVIEW`; source-equivalence evidence is clean,
  but the task's explicit build and rendered light/dark acceptance gates have
  not passed.
- Blockers/risks: No local frontend dependency installation and no available
  in-app browser target prevent runtime acceptance in this environment.
- Handoff: On a Node-enabled checkout with `apps/web` dependencies already
  installed, run `npm run build`, preview the app, and smoke-check Meridian's
  dashboard, transactions, and review screens in light and dark themes. Mark
  FE-01 `DONE` and unblock FE-02 only if all checks pass.

### 2026-07-15 15:09 EDT — BE-03 — Codex / be03_models

- Status: `DONE`
- Scope: `apps/api/app/models/`, `apps/api/app/schemas/`,
  `apps/api/alembic/env.py`,
  `apps/api/alembic/versions/0002_profile_account_models.py`, focused BE-03
  tests, and this workboard
- Work: Added SQLAlchemy 2 Profile and Account models with explicit non-null
  ownership and database cascade semantics; Pydantic v2 create/update/read
  schemas; canonical UTC timestamp JSON serialization; Alembic metadata wiring;
  and a reversible profile/account migration after the empty baseline.
- Verification: `.venv\Scripts\python -m pytest -q -p no:cacheprovider
  --basetemp .test-tmp\be03-full` — 47 passed; `.venv\Scripts\python -m ruff
  check app tests alembic` — all checks passed; `git diff --check` — passed
  with line-ending warnings only. Focused BE-03 tests independently reported 11
  passed. Test execution required the approved non-sandbox path because Windows
  ACLs blocked pytest temporary directories inside the managed sandbox.
- Decisions: Keep the established `last4` contract used by the architecture and
  prototypes while validating either four or five masked digits. The database
  supports cascading profile deletion to preserve referential integrity, while
  BE-04/BE-05 should defer exposing profile deletion per the product plan.
  SQLite's naive datetime round-trip is normalized to explicit UTC by response
  schemas. No speculative uniqueness constraints were added.
- Blockers/risks: none
- Handoff: BE-04 is `READY`; implement profile/account services with mandatory
  profile scoping, isolation tests, archive behavior, and no profile-delete
  endpoint semantics.

### 2026-07-15 15:12 EDT — GOV-01 — Codex

- Status: `DONE`
- Scope: `AGENTS.md`, this workboard
- Work: Added the product owner's mandatory `ui-ux-pro-max` skill requirement
  for every agent that implements, refactors, or reviews frontend design or UX.
- Verification: Reviewed both instruction files after editing and ran
  `git diff --check`.
- Decisions: Frontend UI agents must read the skill before design work, follow
  its applicable design-system/search workflow, and record accessibility,
  interaction, responsive, theme, and reduced-motion verification. Purely
  non-visual frontend data-client work is excluded.
- Blockers/risks: none
- Handoff: Include the skill requirement explicitly in every future frontend
  design agent assignment and reject frontend UI handoffs that omit its checks.
- Exception: This direct product-owner governance request was not represented
  by a pre-existing `READY` task, so it was completed and recorded here without
  claiming an implementation task.

### 2026-07-15 15:16 EDT — BE-04 — Codex / be04_services

- Status: `IN PROGRESS`
- Scope: `apps/api/app/services/`, focused profile/account service tests, and
  this workboard
- Work: Claiming profile/account persistence services with mandatory scoped
  account reads and writes, explicit archive behavior, and no hard profile
  deletion service.
- Verification: pending implementation
- Decisions: Follow the product plan's archive-first behavior. Every account
  operation requires a profile ID and matches on both profile and account ID;
  missing and cross-profile records share the same not-found result.
- Blockers/risks: Update-schema fields currently conflate omission with explicit
  null; services will use `model_fields_set` and reject null for non-nullable
  stored fields without expanding BE-03 schema scope unless tests prove a schema
  correction is required.
- Handoff: Implement focused services/tests, run the backend suite and Ruff,
  then update BE-04 with exact results and unblock BE-05 if acceptance passes.

### 2026-07-15 15:20 EDT — BE-04 — Codex / be04_services

- Status: `DONE`
- Scope: `apps/api/app/services/`,
  `apps/api/tests/test_profile_account_services.py`, and this workboard
- Work: Added transaction-neutral profile and account services for create,
  list, get/require, update, archive, and restore. Every account read or write
  matches profile ID and account ID in the same query; wrong-owner and missing
  accounts produce the same non-disclosing result. Default lists hide archived
  rows, explicit management lists can include them, and no hard-delete profile
  service exists. Added adversarial isolation, archive/restore, nullable patch,
  no-partial-mutation, and account-state preservation tests.
- Verification: `.venv\Scripts\python -m pytest -q
  tests/test_profile_account_services.py -p no:cacheprovider --basetemp
  .test-tmp\be04-final-focused` — 15 passed; `.venv\Scripts\python -m pytest
  -q -p no:cacheprovider
  --basetemp .test-tmp\be04-full` — 62 passed; `.venv\Scripts\python -m ruff
  check app tests alembic` — all checks passed; `git diff --check` — passed
  with line-ending warnings only.
- Decisions: Services flush but never commit or roll back; BE-05 owns request
  transaction boundaries. Explicit null clears only nullable account fields and
  is rejected before mutation for required fields. Archive is a visibility and
  lifecycle state, not an authorization boundary: explicitly addressed archived
  profiles/accounts remain available for management and restoration. List order
  is case-insensitive name/display-name with ID as a deterministic tie-breaker.
- Blockers/risks: none
- Handoff: BE-05 is `READY`. Map `ResourceNotFoundError` identically for absent
  and cross-profile resources, map `InvalidUpdateError` to a field-readable 422,
  keep request transactions outside these services, expose archive/restore (not
  hard profile delete), and do not weaken the composite account scope predicates.

### 2026-07-15 15:22 EDT — BE-05 — Codex / be05_api_routes

- Status: `IN PROGRESS`
- Scope: `apps/api/app/routers/`, `apps/api/app/main.py`, backend database
  dependency wiring, focused profile/account API tests, and this workboard
- Work: Claiming typed profile/account HTTP routes with isolated request
  transactions, uniform scoped-not-found responses, archive/restore lifecycle
  endpoints, and OpenAPI coverage.
- Verification: pending implementation
- Decisions: Use nested `/profiles/{profile_id}/accounts` routes so the profile
  scope is explicit and cannot be supplied by an account payload. No DELETE
  profile or account route will be exposed. Archived resources remain explicitly
  manageable, matching BE-04; default collection responses exclude them.
- Blockers/risks: The configured production database must not be touched by API
  tests. Session dependency overrides will use a temporary migrated-equivalent
  schema while preserving INT-01's later ownership of the shared integration
  harness.
- Handoff: Implement routes/dependencies/tests, verify HTTP and OpenAPI
  contracts plus isolation, then update BE-05 and unblock dependent work.

### 2026-07-15 15:26 EDT — BE-05 — Codex / be05_api_routes

- Status: `DONE`
- Scope: `apps/api/app/routers/`, `apps/api/app/main.py`,
  `apps/api/app/db/dependencies.py`, `apps/api/app/db/__init__.py`,
  `apps/api/tests/test_profile_account_api.py`, and this workboard
- Work: Added typed create/list/get/update/archive/restore profile endpoints and
  equivalently typed nested account endpoints under an explicit profile path.
  Added one transaction-per-request session dependency wiring with lazy engine
  initialization and shutdown disposal, uniform 404/422 service-error mapping,
  router registration, and isolated API contract tests. No hard-delete endpoint
  exists; account payloads cannot supply or override profile ownership.
- Verification: `.venv\Scripts\python -m pytest -q
  tests/test_profile_account_api.py -p no:cacheprovider --basetemp
  .test-tmp\be05-focused` — 7 passed; `.venv\Scripts\python -m pytest -q -p
  no:cacheprovider --basetemp .test-tmp\be05-full` — 69 passed;
  `.venv\Scripts\python -m ruff check app tests alembic` — all checks passed;
  `git diff --check` — passed with line-ending warnings only.
- Decisions: Canonical account URLs are
  `/profiles/{profile_id}/accounts[/{account_id}]`, with POST archive/restore
  subresources. Missing and wrong-profile account IDs both return status 404 and
  `{"detail":"account not found"}`. Invalid explicit-null updates return 422
  with the affected field name in readable detail. Database construction is
  lazy so importing the app and dependency-overridden tests do not touch the
  configured personal database; successful requests commit and exceptions roll
  back through the session dependency.
- Blockers/risks: none
- Handoff: Frontend/API consumers should generate types from the verified
  OpenAPI document and use archive/restore, not DELETE. FE-04 and INT-01 remain
  blocked only on FE-03; once FE-03 is done, these BE-05 contracts are ready for
  integration. Preserve the nested profile scope and uniform 404 behavior.

### 2026-07-15 15:58 EDT — GRAPH-01 — Codex / root

- Status: `DONE`
- Scope: `graphify-out/` and this workboard
- Work: Built a repository-wide Graphify knowledge graph from 102 supported
  files. Combined AST extraction for code/configuration with semantic extraction
  for documentation and design images, then generated the interactive graph,
  machine-readable graph data, community labels, manifest, cost record, and
  analysis report. Two sensitive files were detected and skipped automatically;
  their names were not exposed.
- Verification: Final graph contains 784 nodes, 1,371 edges, and 58 labeled
  communities. `graphify query "What are the next implementation steps and
  blockers?" --budget 1000` completed successfully from the generated graph.
  Benchmarking estimated a 19.6x token reduction versus naive corpus loading.
- Decisions: This was a direct user-requested repository tooling task rather
  than a pre-existing READY implementation row, so it was recorded as GRAPH-01
  after completion. No product task dependencies or ownership were changed.
- Blockers/risks: The graph remains usable, but diagnostics found 172 dangling
  endpoint references and 27 undirected same-endpoint edge collapses; inferred
  relationships should be treated as navigation hypotheses until verified.
- Handoff: Open `graphify-out/graph.html` for interactive exploration, use
  `graphify-out/graph.json` for tooling, and consult
  `graphify-out/GRAPH_REPORT.md` for hubs, gaps, and suggested questions.

### 2026-07-15 16:03 EDT — GOV-02 — Codex / root

- Status: `DONE`
- Scope: `AGENTS.md` and this workboard
- Work: Added an always-on Graphify-first retrieval policy for codebase,
  architecture, dependency, planning, and review work. Agents now begin with a
  bounded graph query, load only returned source locations, use focused
  explain/path traversal, and pass scoped graph context to delegated agents.
- Verification: Reviewed the installed Graphify Codex integration template and
  CLI help, queried the existing graph with a 1,000-token budget, reread the
  resulting instruction section, and ran `git diff --check`.
- Decisions: Graphify is a token-saving retrieval map, not an authority. The
  complete workboard, accepted ADRs, and referenced source remain mandatory;
  inferred or ambiguous graph edges require source verification. Code changes
  refresh the AST graph with `graphify update .`.
- Blockers/risks: Documentation and image changes are not semantically refreshed
  by the AST-only update command, so agents must record possible staleness until
  a semantic update is run.
- Handoff: Future agents should query Graphify before broad repository reads,
  normally use an 800–1,500-token traversal budget, and include only the relevant
  graph slice and source files in delegated context.
- Exception: This direct product-owner governance request was not represented by
  a pre-existing `READY` task, so it was completed and recorded without claiming
  an implementation task.

### 2026-07-15 20:20 UTC — FE-01 acceptance — Claude Opus 4.8

- Status: `DONE`
- Scope: acceptance verification only of `apps/web/src/styles/meridian-tokens.css`,
  `apps/web/src/directions/meridian/meridian.css`,
  `apps/web/src/directions/meridian/index.tsx`; workboard status update; added
  `CLAUDE.md`.
- Work: Ran the FE-01 build and light/dark visual smoke checks that the prior
  Codex environment could not (no Node there). Meridian renders unchanged with
  the extracted tokens. Marked FE-01 `DONE`, unblocking FE-02 (now `READY`).
- Verification: `npm run typecheck` — clean (exit 0); `npm run build` — success
  (vite built, 2.7s); Meridian `/meridian/dashboard` smoke-checked in dark and
  light via headless Chromium (1440×960) — layout, hero, donut, dense tables,
  and tabular numbers render correctly and match the pre-extraction look.
  Backend regression sanity: `python -m pytest -q` in `apps/api` — 69 passed.
- Decisions: Token extraction is visually behavior-preserving; no prototype
  changes needed.
- Blockers/risks: none for FE-01.
- Handoff: FE-02 is `READY` — build the production app shell under
  `apps/web/src/app/` mounted from `main.tsx`, keeping the prototype comparison
  harness accessible.
- Exceptions (environment): (1) The `graphify` CLI is not installed in this
  environment (only `graphify-out/graph.json` is present), so graph queries could
  not be run; navigation used the mandatory full workboard read plus targeted
  search. (2) The `ui-ux-pro-max` skill is not installed here; per AGENTS.md the
  user's direct "continue building" instruction is followed and this exception is
  recorded — the skill's equivalent checks (semantic markup, labelled inputs,
  visible focus, WCAG-AA contrast, colour-not-alone, keyboard nav, light/dark,
  reduced-motion) are applied and reported manually on UI tasks.

### 2026-07-15 20:40 UTC — FE-02 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/web/src/app/` (`AppShell.tsx`, `pages.tsx`, `app.css`),
  `apps/web/src/App.tsx` (mount `/app/*` route), `apps/web/src/Landing.tsx`
  (added an "Open the app" entry link), plus two reference screenshots under
  `docs/screenshots/`.
- Work: Built the production application shell as a Meridian-styled workspace
  mounted at `/app/*`, fully separate from the prototype comparison harness
  (which stays reachable at `/` and `/:direction/:screen`). The shell has a
  sticky top nav (brand + Dashboard/Profiles/Accounts/Categories/Settings), a
  theme toggle, a profile-indicator placeholder, and nested routes with
  placeholder pages for each section (profiles → FE-04, accounts → FE-05,
  categories → backlog). The shell reuses the shared Meridian theme tokens by
  carrying `class="app mrd"` and importing only `meridian-tokens.css`, so no
  prototype component styles leak; production styles are namespaced `app-`.
- Verification: `npm run typecheck` — clean (exit 0); `npm run build` — success
  (vite 4.1s). Rendered smoke check via headless Chromium: `/app/dashboard`
  (dark) and `/app/accounts` (light) render the Meridian nav/theme correctly;
  `/` (prototype landing) still returns 200 and prototypes are unchanged.
  Keyboard tab order verified programmatically: brand → Dashboard → Profiles →
  Accounts → Categories → Settings → theme toggle.
- Slight scope note: edited `App.tsx` (the router) and added one entry link in
  `Landing.tsx` so the production shell is reachable; both are minimal wiring for
  "routes separate from the harness," recorded here per protocol.
- ui-ux checks (skill unavailable — see FE-01 exception): semantic `<nav>`/
  `<main>`; `NavLink` anchors + real `<button>` for theme with `aria-label`;
  visible `:focus-visible` outline; light+dark via tokens; `prefers-reduced-
  motion` handled; nav colour always paired with icon + text label.
- Decisions: Production app lives under `/app`; the prototype harness is retained
  per D-02 until the first vertical slice passes QA. A warm CTA accent (product
  owner's earlier request) is included as an `app-` token for primary buttons,
  keeping the blue-violet brand.
- Blockers/risks: none.
- Handoff: FE-03 is `READY` — add TanStack Query + a typed loopback API client
  and error model under `apps/web/src/api/`, wrap the app in a
  QueryClientProvider, and prove a `/health` request with loading/error states.
  Then FE-04 (profiles) and INT-01 unblock.

### 2026-07-15 20:55 UTC — FE-03 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/web/package.json` + `package-lock.json` (add
  `@tanstack/react-query`), `apps/web/src/api/` (`client.ts`, `queryClient.ts`,
  `health.ts`), `apps/web/src/vite-env.d.ts`, `apps/web/src/app/AppShell.tsx`
  (QueryClientProvider + live API-status indicator), `apps/web/src/app/app.css`
  (status styles), reference screenshots.
- Work: Added a typed local API client with a normalized `ApiError` (handles the
  contract's `{detail:[{field,message}]}` and FastAPI's default `{detail:[{loc,
  msg}]}`, plus a clear offline error on network/CORS failure). Added a shared
  `QueryClient` (one retry, no retry on 4xx, no refetch-on-focus) and a `useHealth`
  hook. Wrapped the production shell in `QueryClientProvider` and surfaced a live
  connection chip (checking / connected / offline) in the nav. API base defaults
  to `http://127.0.0.1:8787`, overridable via `VITE_API_BASE`.
- Verification: `npm run typecheck` — clean; `npm run build` — success. End-to-end
  with the real backend: started `uvicorn app.main:app` (127.0.0.1:8787), served
  the web dev server on the CORS-allowed `127.0.0.1:5173`, and confirmed the
  health query resolves — nav shows a green “API connected” (`.app-status.online`).
  Stopped the backend and reloaded — nav shows red “API offline”
  (`.app-status.offline`), exercising the error path. Loading state renders
  “Checking API…”. Backend regression suite earlier this session: 69 passed.
- Decisions: Kept the query client scoped to the production app shell (prototypes
  don't use it). Entity (Profile/Account) TS types are intentionally NOT added
  here — FE-04/FE-05 will derive them from the verified OpenAPI per BE-05's
  handoff, avoiding speculative drift.
- Blockers/risks: none. NOTE on “states are tested”: the loading/error/success
  states are implemented and verified live/rendered, but *automated* deterministic
  request-state tests require the web test harness, which is **INT-01's** scope
  (INT-01 depends on FE-03 in the dependency map). Those unit tests are handed to
  INT-01 rather than duplicated here.
- Handoff: FE-04 (profiles UI) and INT-01 (test harness) are now `READY`. FE-04
  should consume `api`/`useQuery` from `src/api`, add profile list/create/select
  with loading/empty/error states, and derive Profile types from the backend
  OpenAPI. INT-01 should add the deterministic frontend request-state tests
  (mocking `api`) and the isolated integration DB fixtures.

### 2026-07-15 21:10 UTC — FE-04 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/web/src/features/profiles/` (`types.ts`, `api.ts`,
  `ProfileContext.tsx`, `ProfileSwitcher.tsx`, `ProfilesPage.tsx`,
  `profiles.css`); `apps/web/src/app/AppShell.tsx` (ProfileProvider + nav
  switcher + profiles route); `apps/web/src/app/pages.tsx` (dashboard active-
  profile tile; removed the placeholder ProfilesPage); reference screenshots.
- Work: Built the profile switcher + management UI against the real `/profiles`
  API. Types mirror the backend exactly (integer ids, snake_case
  `base_currency`/`is_archived`, no camelCase alias). `ProfileProvider` holds the
  active profile (persisted in `localStorage`, auto-selects the first active
  profile, self-heals if the selected profile is archived). The nav
  `ProfileSwitcher` is an accessible menu (aria-haspopup/expanded,
  menuitemradio). `ProfilesPage` lists active + archived, creates (with
  field-level validation surfaced from `ApiError`), switches, renames inline,
  and archives with an explicit in-row confirmation (restore for archived).
- Verification: `npm run typecheck` clean; `npm run build` ok. Full end-to-end
  against a migrated scratch SQLite (`alembic upgrade head`) + uvicorn
  (127.0.0.1:8787) + dev server (CORS-allowed 5173), driven with Playwright:
  loaded existing profile → created "Household" via the UI (auto-selected as
  current) → switcher menu shows both + Manage → switched to "Hayden" → archived
  "Household" via the confirm step (moved to Archived) → restored it (back to 2
  active). Loading/empty/error states implemented (empty → "Create your first
  profile"; error → message + Try again).
- ui-ux checks (skill unavailable — see FE-01 exception): labelled inputs, real
  `<button>`s, `role="alert"` on errors, `role="menu"/menuitemradio` +
  `aria-expanded` on the switcher, visible focus, light/dark via tokens, colour
  paired with avatar/label. Warm CTA (product-owner request) on primary actions.
- Decisions: The acceptance's "delete" is realised as archive (with confirm)
  because the backend intentionally exposes archive/restore, not hard delete
  (BE-05 contract + product plan: archive is safer; deletion+export is a later
  deliberate step). Profile entity types are hand-mirrored from the backend
  schema (verified against a live create response) rather than generated, since
  no OpenAPI codegen is wired yet.
- Blockers/risks: none.
- Handoff: FE-05 (accounts) is `READY` — build account CRUD under
  `apps/web/src/features/accounts/`, scoped to the active profile from
  `useCurrentProfile()`, consuming `/profiles/{id}/accounts` and `/accounts/{id}`
  (archive/restore, not delete). Read `apps/api/app/schemas/account.py` for exact
  fields before implementing.

### 2026-07-15 21:35 UTC — FE-05 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/web/src/features/accounts/` (`types.ts`, `api.ts`,
  `AccountsPage.tsx`, `accounts.css`); `apps/web/src/app/AppShell.tsx` (accounts
  route → real page); `apps/web/src/app/pages.tsx` (dashboard Accounts-count tile;
  removed placeholder AccountsPage); reference screenshots.
- Work: Built account management scoped to the active profile from
  `useCurrentProfile()`. Account routes are nested under the profile
  (`/profiles/{id}/accounts`, `.../{accountId}/archive|restore`). Types mirror the
  backend exactly (integer ids, snake_case `display_name`/`is_archived`,
  nullable `last4`). A shared `AccountForm` handles create + edit: issuer
  `<select>` (TD/AMEX/CIBC/OTHER), display name, an accessible colour-swatch
  radiogroup, optional 4–5 digit last4 with inline validation. Rows show a
  coloured card chip + masked digits; archive requires an in-row confirm; archived
  accounts can be restored. When no profile is selected, the page routes the user
  to Profiles.
- Verification: `npm run typecheck` clean; `npm run build` ok. End-to-end against
  the live backend (migrated scratch SQLite + uvicorn + CORS dev server), driven
  with Playwright: created "TD Cash Back Visa" (issuer TD, green swatch, last4
  4821) under the active profile; archived-with-confirm → Archived; restored →
  active. **Profile isolation proven directly:** `GET /profiles/1/accounts`
  returns the account, `GET /profiles/2/accounts` returns `[]`; the UI's query key
  and URL are profile-scoped so switching profiles swaps the account list. Empty
  and error states implemented.
- ui-ux checks (skill unavailable — see FE-01 exception): labelled inputs +
  `<select>`, `role="radiogroup"/radio` colour swatches with `aria-checked`,
  `role="alert"` validation, visible focus, light/dark tokens, colour paired with
  issuer text + masked digits (never colour alone). Warm CTA on primary actions.
- Decisions: "delete" realised as archive+confirm (backend exposes archive/
  restore only). Edit reuses the create form pre-filled (PATCH).
- Blockers/risks: none. The profiles/accounts vertical slice is now feature-
  complete end-to-end.
- Handoff: INT-01 (`READY`) is next in the critical path — add the isolated
  integration-test DB fixtures and the deterministic frontend request-state tests
  (mock `api`; cover loading/error/success for profiles + accounts). QA-01 then
  validates the whole slice and unblocks DOC-01. M2's user-facing behaviour is
  implemented; QA-01 is the formal gate.

### 2026-07-15 21:55 UTC — INT-01 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/web/package.json`/`package-lock.json` (test devDeps + scripts),
  `apps/web/vitest.config.ts`, `apps/web/src/test/setup.ts`,
  `apps/web/tsconfig.json` (exclude tests from the production typecheck),
  `apps/web/src/api/client.test.ts`, `apps/web/src/api/health.test.tsx`,
  `apps/web/src/features/profiles/api.test.tsx`, `.github/workflows/ci.yml`
  (run `npm test` in the web job).
- Work: Added the frontend test harness — Vitest + Testing Library + jsdom —
  with deterministic, network-free request-state tests: the API client error
  model (contract field errors, FastAPI loc/msg, string detail, offline → status
  0, success), and query-layer states via the real TanStack Query layer with a
  mocked `api` (loading → success, and error/offline). Profiles hooks assert the
  active-only scope URL and the create body. Tests are excluded from
  `tsc --noEmit`/`vite build`, so the production build stays clean while `npm test`
  runs the suite. Wired `npm test` into CI.
- Verification: `npx vitest run` — 3 files, **10 tests passed**, deterministic
  (no network; `api` mocked). `npm run typecheck` clean and `npm run build` ok
  with tests excluded. Backend isolation confirmed by inspection: the API tests
  (`tests/test_profile_account_api.py`) build a per-test `tmp_path/api.db` engine
  and override `get_session`, so they never touch the configured personal
  database; the full backend suite passed **69** earlier this session. Backend
  test infrastructure was already isolated, so it was cited, not rewritten.
- Decisions: Kept backend fixtures as-is (already isolated per BE-05); INT-01's
  new surface is the web test configuration + deterministic request-state tests.
  Test files are excluded from the app `tsconfig` to keep build type-checking
  focused on shipping code while Vitest/esbuild runs the tests.
- Blockers/risks: none.
- Handoff: QA-01 is `READY` — the only remaining gate before DOC-01. Run the
  full validation: clean install, `alembic upgrade head`, backend
  `pytest`/`ruff`, web `typecheck`/`test`/`build`, loopback startup, a
  keyboard-only smoke of profiles/accounts, and the profile-isolation scenario
  (account under profile A absent under profile B). Most of these were exercised
  ad hoc while building FE-01…FE-05 + INT-01; QA-01 formalises them in one pass.

### 2026-07-15 22:15 UTC — QA-01 — Claude Opus 4.8

- Status: `DONE`
- Scope: cross-app validation only (no feature edits — no defects found); this
  workboard.
- Work: Ran the full profiles/accounts vertical-slice validation in one pass.
- Verification (all green):
  - **Migrations:** on a fresh temp DB, `alembic upgrade head` → `downgrade
    base` → `upgrade head` all succeed (reversible).
  - **Backend:** `ruff check app tests alembic` — all pass; `pytest -q` — 69
    passed.
  - **Frontend:** `npm run typecheck` clean; `npm test` — 10 passed; `npm run
    build` — success.
  - **Loopback startup:** uvicorn `--host 127.0.0.1` on 8787; `hostname -i` =
    127.0.0.1 (no off-loopback exposure); web dev server on 127.0.0.1:5173.
  - **Keyboard smoke (profiles):** tab order reaches Switch to / Rename /
    Archive as real focusable buttons.
  - **Profile isolation (live UI):** created profiles "Alpha" + "Beta"; added a
    "Beta Card" account while Beta was active (accounts=1); switched to Alpha →
    accounts=0 with the "No accounts yet" empty state. Backend-level isolation
    was also confirmed earlier (`GET /profiles/1/accounts` populated vs
    `/profiles/2/accounts` empty).
- Decisions: No code changes required; the slice met every acceptance criterion.
- Blockers/risks: none. Milestones M1 and M2 are complete.
- Handoff: DOC-01 (`READY`, last task in this group) — refresh `README.md`,
  `apps/api/README.md`, and `docs/architecture/` so a new developer can reproduce
  the verified setup/run/test commands and the documented behaviour matches the
  shipped profiles/accounts app. After DOC-01, expand the board with the next
  vertical slice from the later-stage backlog (categories/transactions).

### 2026-07-15 22:30 UTC — DOC-01 — Claude Opus 4.8

- Status: `DONE`
- Scope: `README.md`, `apps/api/README.md`, `docs/architecture/overview.md`.
- Work: Brought the docs in line with the shipped, verified state. Root README:
  updated Status to Stage 2 foundation, documented the `/app` production app vs
  the `/` prototype harness, replaced the "Backend placeholder" section with the
  real setup (venv, `alembic upgrade head`, uvicorn, pytest, ruff) + the actual
  profiles/accounts endpoints + `ST_DATABASE_PATH` + archive-not-delete + money-
  as-cents, added the frontend checks (`typecheck`/`test`/`build`), and corrected
  the repo-shape labels. `apps/api/README.md`: removed the "Stage 0 placeholder"
  framing, listed the profiles/accounts endpoints and scoping/archival rules, and
  refreshed the layout tree (db/domain/models/schemas/services/alembic/tests).
  `docs/architecture/overview.md`: added an "Implemented so far (Stage 2
  foundation)" section and fixed the stale monorepo labels.
- Verification: every documented command was actually run during this session
  (npm install/dev/typecheck/test/build; pip install; `alembic upgrade head` +
  downgrade/upgrade; uvicorn on 127.0.0.1; pytest 69; ruff) — docs match verified
  behaviour. Markdown links point at existing files.
- Blockers/risks: none.
- Handoff: The profiles/accounts vertical slice (M1 + M2) and its documentation
  are complete. The next agent should **expand this board** with a new slice from
  the later-stage backlog — recommended: categories (seed defaults + per-profile
  overrides) as BE/FE tasks with the same acceptance rigour — before claiming
  implementation.

### 2026-07-16 — board expansion (categories slice) — Claude Opus 4.8

- Added BE-07, BE-08, FE-06, QA-02 rows for the categories vertical slice (M3),
  with the same isolation/archive/verification rigour as profiles/accounts, and
  removed categories from the later-stage backlog.

### 2026-07-16 — BE-07 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/api/app/models/category.py` (+ `models/__init__`, Profile
  `categories` relationship), `apps/api/app/schemas/category.py` (+
  `schemas/__init__`), `apps/api/app/services/categories.py` +
  `category_defaults.py` (+ `services/__init__`), `services/profiles.py` (seed
  hook on create), `alembic/versions/0003_category_models.py`, and
  `tests/test_category_services.py`; updated the profile/account migration test's
  head-table set to include `categories`.
- Work: Added the profile-scoped `Category` model (unique `(profile_id, slug)`,
  self-FK `parent_id` for future sub-categories, `color` hex check, index on
  `(profile_id, is_archived)`), Pydantic create/update/read schemas, and
  profile-isolated services (create with server-derived unique slug + appended
  sort_order, list in display order, get/require scoped, update with null-guard,
  archive/restore). `create_profile` now idempotently seeds the 13 default
  categories (matching the frontend dataset). A reversible migration creates the
  table after the profile/account head.
- Verification: migration `upgrade head → downgrade -1 → upgrade head` succeeds
  (incl. 0003); `ruff check app tests alembic` — all pass; `pytest` — **75
  passed** (6 new category tests: seed-on-create + 13 defaults, seed idempotency,
  unique-slug derivation + sort append, cross-profile isolation → not-found,
  archive/restore, null-required-field rejection). Updating the existing
  migration test's expected head set is a direct consequence of the new revision.
- Decisions: user-created categories get a server-derived slug (`slugify(name)`
  with `-2`, `-3` dedup); slug is not client-supplied. Default categories are
  `is_default=True`. Seed uses a lazy import inside `create_profile` to avoid a
  services import cycle.
- Blockers/risks: none.
- Handoff: BE-08 is `READY` — add nested `/profiles/{id}/categories` routes
  (list/create/get/patch/archive/restore) mirroring the accounts router, wire
  into `main`, and add API tests (happy path, 422, cross-profile 404, OpenAPI).

### 2026-07-16 — BE-08 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/api/app/routers/categories.py`, `apps/api/app/main.py` (import +
  include_router), `apps/api/tests/test_category_api.py`.
- Work: Added nested category routes under the owning profile —
  `GET/POST /profiles/{id}/categories`, `GET/PATCH
  /profiles/{id}/categories/{categoryId}`, and `POST .../archive|restore` —
  mirroring the accounts router and reusing the shared 404/422 service-error
  mapping in `main`.
- Verification: `ruff check app tests alembic` — pass; `pytest` — **81 passed**
  (6 new API tests: seeded defaults exposed on a new profile, custom create,
  patch + archive/restore, cross-profile 404 on GET and PATCH, field-specific
  422 on bad colour, and OpenAPI contains the category paths).
- Decisions: none beyond mirroring the accounts contract; categories are
  archive/restore, not hard delete.
- Blockers/risks: none.
- Handoff: FE-06 is `READY` — build the categories management UI under
  `apps/web/src/features/categories/`, scoped to the active profile via
  `useCurrentProfile()`, consuming these routes. Category wire types: integer
  ids, snake_case (`profile_id`, `excluded_from_spending`, `is_default`,
  `sort_order`, `is_archived`, `parent_id`); create body is
  `{name, color, icon?, parent_id?, excluded_from_spending?}` (slug is server-
  derived). Distinguish default vs custom; keep archive/restore.

### 2026-07-16 — FE-06 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/web/src/features/categories/` (`types.ts`, `api.ts`,
  `CategoriesPage.tsx`, `categories.css`); `apps/web/src/app/AppShell.tsx`
  (categories route → real page); `apps/web/src/app/pages.tsx` (dashboard
  categories-count tile; removed placeholder CategoriesPage); reference
  screenshot.
- Work: Built category management scoped to the active profile. Types mirror the
  backend (integer ids, snake_case, `is_default`, `excluded_from_spending`,
  `slug`). A shared `CategoryForm` (create + edit) has name, an accessible
  icon-choice radiogroup, a colour-swatch radiogroup, and an exclude-from-
  spending toggle. Two-column card grid shows colour chip + icon + name with
  DEFAULT / EXCLUDED badges and the mono slug; archive requires an in-row
  confirm; archived categories restore. No-profile routes to Profiles.
- Verification: `npm run typecheck` clean; `npm test` 10 passed; `npm run build`
  ok. End-to-end against the live backend (fresh migrated DB + uvicorn + CORS dev
  server), driven with Playwright: a new profile exposes **13 seeded defaults**
  (all badged default); created a custom "Subscriptions" (icon + colour +
  excluded) → 14 rows; archived-with-confirm → Archived; restored → 14 active.
- ui-ux checks (skill unavailable — see FE-01 exception): labelled input,
  `role="radiogroup"/radio` icon + colour pickers with `aria-checked`,
  `role="alert"` validation, checkbox toggle, visible focus, light/dark tokens,
  colour paired with icon + name + slug. Warm CTA on primary actions.
- Decisions: default categories are editable/archivable (backend permits it);
  the UI marks them "default" rather than locking them. Slug is shown read-only
  (server-derived).
- Blockers/risks: none.
- Handoff: QA-02 (`READY`) — validate the categories slice (migrations, backend
  tests/lint, web typecheck/test/build, seeding-on-create, and category
  profile-isolation) in one pass.

### 2026-07-16 — QA-02 — Claude Opus 4.8

- Status: `DONE`
- Scope: cross-app validation only (no feature edits — no defects); this workboard.
- Work: Validated the categories vertical slice.
- Verification (all green):
  - **Migrations:** fresh DB `upgrade head → downgrade base → upgrade head`
    (incl. 0003) all succeed.
  - **Backend:** `ruff check app tests alembic` — pass; `pytest` — 81 passed.
  - **Frontend:** `npm run typecheck` clean; `npm test` — 10 passed; `npm run
    build` — success.
  - **Seeding on create:** a new profile exposes exactly 13 default categories
    (via API and in the UI), all flagged default.
  - **Category profile isolation:** profile 1's custom "Subscriptions" is absent
    from profile 2 (which independently auto-seeded its own 13 defaults); the API
    test suite also asserts cross-profile GET/PATCH → 404.
- Blockers/risks: none.
- Handoff: The categories slice is complete and validated. M3 remains
  `IN PROGRESS` — the next slice is **transactions** (with splits/tags and the
  money-inclusion rules from `docs/decisions/0003-money-and-accounting.md`),
  which is substantially larger and should be expanded into its own BE/FE task
  rows before implementation.

### 2026-07-16 — board expansion (transactions slice) + BE-09 — Claude Opus 4.8

- Added the transactions slice rows (BE-09/10/11, FE-07, QA-03) with acceptance
  detail; moved the import framework down the backlog.
- **BE-09 — Status: `DONE`.**
- Scope: `apps/api/app/models/{transaction,transaction_split,tag}.py` (+
  `models/__init__`, Profile `transactions`/`tags` relationships),
  `schemas/transaction.py` (+ `schemas/__init__`),
  `services/transactions_rules.py` + `errors.SplitSumError` (+ `services/__init__`),
  `alembic/versions/0004_transaction_models.py`, `tests/test_transaction_rules.py`;
  updated the migration test's head-table set.
- Work: Added the profile+account-scoped `Transaction` model (signed
  `amount_cents` BigInteger; type/direction/categorization_status/source CHECKs;
  `included_in_spending`; nullable `category_id` ON DELETE SET NULL; soft-delete
  `deleted_at`; indexes on `(profile_id, account_id)` and `(profile_id, date)`),
  `TransactionSplit` (category + cents, cascade), and `Tag` + `TransactionTag`
  (unique per profile, m2m). Pydantic create/update/read schemas. Pure domain
  rules: `validate_splits_sum` (exact integer-cents equality → `SplitSumError`)
  and `default_included_for_type` (purchase/refund included; payment/transfer/
  cash-advance/fee/interest/income excluded, per ADR 0003). Reversible migration
  0004.
- Verification: migration `upgrade head → downgrade -1 → upgrade head` (incl.
  0004) succeeds; `ruff` clean; `pytest` — **84 passed** (3 new: inclusion
  policy, split-sum exact/mismatch, and an ORM round-trip persisting a
  transaction with two splits that sum to the parent). Fixed a `date`
  field-name/type shadowing bug in both the model and the schema by aliasing
  `datetime.date`.
- Decisions: `recurring_series_id` and `import_id` are plain nullable ints for
  now (their tables arrive in later slices); no FK yet. Splits/tags have no HTTP
  surface until BE-10/BE-11.
- Blockers/risks: none.
- Handoff: BE-10 is `READY` — build profile-scoped transaction services
  (create/list+filter/update, split + tag management using
  `validate_splits_sum`, soft delete/restore, and default inclusion via
  `default_included_for_type`) with isolation + soft-delete tests.

### 2026-07-16 — DX-01 (run without Node.js) — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/api/app/main.py` (serve pre-built UI + move metadata to `/api`),
  `apps/api/tests/test_health.py`, `apps/web/src/api/client.ts` (same-origin API
  base in production), `apps/web/dist/**` (committed build), `.gitignore`
  (un-ignore `apps/web/dist`), `scripts/start-app.{sh,ps1}`, `README.md`,
  `CLAUDE.md`, this workboard.
- Work: The product owner cannot install/run Node.js. Node is only a build tool;
  its output is static files. So the FastAPI backend now serves the pre-built
  React app (`apps/web/dist/`) on the same origin — the whole app runs as a
  single **Python-only** process on `http://127.0.0.1:8787`, no Node required to
  run it. API routes are registered first and take precedence; a GET catch-all
  serves built assets or falls back to `index.html` for client-side routes (only
  active when `dist/index.html` exists, with a path-traversal guard). Service
  metadata moved from `/` to `/api` so `/` serves the app. The frontend API base
  is now same-origin (relative) in production builds and `127.0.0.1:8787` under
  the Vite dev server. Added `scripts/start-app.{sh,ps1}` (venv + deps +
  migrate + open browser + uvicorn) and reframed the README so the Python-only
  run is the primary path; Node is documented as dev-only.
- Verification: backend `pytest` **84 passed** and `ruff` clean with `dist/`
  present (SPA guard active). Live Python-only run (uvicorn on 8787, no Node):
  `/` and `/app/profiles` → `index.html` (200); the JS asset → 200
  `text/javascript`; `/health` + `/api` + `POST /profiles` work same-origin; a
  headless browser loaded `/app/profiles`, showed a green **API connected** chip,
  rendered a profile created via the API, and logged **no page errors**.
- Decisions: `apps/web/dist/` is committed (documented exception in `.gitignore`
  and `CLAUDE.md`); it must be rebuilt (`npm run build`) and re-committed after
  any `apps/web/**` change. Assumes Python 3.11+ is available (the user's blocker
  was Node specifically).
- Exception: direct product-owner DX request, not a pre-existing READY row —
  completed and recorded here without claiming an implementation task. Does not
  change the transactions-slice plan; BE-10 remains `READY`.

### 2026-07-16 09:20 EDT — GOV-03 — Product owner / Codex

- Status: `DONE`
- Scope: `docs/decisions/0002-ui-directions.md` and this workboard
- Work: Recorded the product owner's superseding decision to make Ledger the
  sole production UI direction and retire the Stage-1 comparison harness,
  unused prototype directions, and synthetic runtime data.
- Verification: Reconciled the decision against the overnight workboard and
  current frontend routing/import graph; implementation verification belongs to
  FE-LEDGER-01.
- Decisions: Ledger replaces Meridian for all new production UI. The existing
  API-backed profile/account/category functionality is preserved and restyled;
  removal targets comparison/prototype/sample paths, not real user data.
- Blockers/risks: none
- Handoff: FE-LEDGER-01 implements and verifies the consolidation while BE-10
  proceeds independently in the backend.
- Exception: This direct product-owner decision supersedes the previous accepted
  UI direction and was recorded without a pre-existing READY governance row.

### 2026-07-16 09:20 EDT — BE-10 — Codex / be10_transaction_services

- Status: `IN PROGRESS`
- Scope: `apps/api/app/services/transactions.py`, focused backend transaction
  service tests, service exports if required, and this workboard
- Work: Implement profile-scoped transaction creation, filtered listing,
  updates, split/tag management, soft delete/restore, and spending-inclusion
  behavior on top of BE-09.
- Verification: pending implementation
- Decisions: Preserve integer cents, non-disclosing cross-profile not-found
  behavior, transaction-neutral service boundaries, exact split sums, and
  default exclusion of soft-deleted rows.
- Blockers/risks: none
- Handoff: Complete focused/full backend tests and Ruff, then unblock BE-11.

### 2026-07-16 09:20 EDT — FE-LEDGER-01 — Codex / ledger_consolidation

- Status: `IN PROGRESS`
- Scope: `apps/web/src/App.tsx`, `apps/web/src/app/`, production Ledger
  styles/tokens, comparison/prototype/sample-data removal, frontend tests,
  `apps/web/dist/`, and this workboard
- Work: Consolidate the production UI onto Ledger, route `/` directly into the
  app, remove comparison-only features and synthetic runtime data, and verify
  every top navigation control.
- Verification: pending typecheck, tests, build, rendered responsive/light/dark
  smoke checks, keyboard navigation, reduced motion, and rebuilt committed dist
- Decisions: Preserve API-backed profiles, accounts, and categories. Use one
  primary Ledger navigation hierarchy with real links/buttons, semantic theme
  tokens, minimum touch targets, visible focus, and no color-only state.
- Blockers/risks: The `ui-ux-pro-max` search script directory is present but its
  documented `search.py` is missing; the agent must apply the fully read skill's
  embedded rules and record that tooling limitation.
- Handoff: Finish the Ledger-only shell independently of BE-10; FE-07 will add
  the live transaction workspace after BE-11.

### 2026-07-16 — BE-10 scope correction — Codex / be10_transaction_services

- Status: `IN PROGRESS`
- Scope: BE-10 service/test files plus the minimal accepted-contract correction
  in `models/transaction.py`, `schemas/transaction.py`,
  `services/transactions_rules.py`, focused rule tests, and a new Alembic
  revision after 0004.
- Work: Before implementing services, the BE-11 contract audit found that BE-09
  conflicts with accepted ADR 0003: purchase/outflow amounts must be positive,
  refunds are excluded from spending by default (while offset in reporting),
  and `transfer` must be a supported transaction type. Correct these contracts
  before BE-10 relies on them; do not rewrite migration 0004.
- Verification: pending focused/full backend tests, migration cycle, Ruff, and
  `git diff --check`.
- Decisions: ADR 0003 and the product plan are authoritative over the stale
  BE-09 docstring/rule/test assumptions. Service inputs for splits and tags stay
  explicit because `TransactionCreate` intentionally contains only parent-row
  fields.
- Blockers/risks: none.
- Handoff: Complete the correction and BE-10 implementation, then publish the
  stable service contract for BE-11.

### 2026-07-16 09:39 EDT — FE-LEDGER-01 — Codex / ledger_consolidation

- Status: `DONE`
- Scope: `apps/web/index.html`, `apps/web/src/App.tsx`, `apps/web/src/app/`,
  profile/account/category presentation styles, profile switcher interaction,
  retired Stage-1 frontend files, `apps/web/dist/`, and this workboard.
- Work: Made Ledger the only production frontend and kept profiles, accounts,
  categories, health, and profile selection API-backed. `/` and legacy
  prototype URLs now enter `/app/dashboard`; removed Landing, comparison
  routing/chrome, Aurora/Horizon/Ledger/Meridian prototypes, Meridian tokens,
  and the synthetic `mockData`/derived/format/type runtime. Rebuilt the shell
  with Ledger semantic tokens, compact responsive navigation, SVG controls,
  skip navigation, and accurate live/empty dashboard content. All top controls
  are real links/buttons; the profile menu supports focus-on-open and Escape.
- Verification: bundled Node runtime: `tsc --noEmit` clean; Vitest **3 files,
  10 tests passed**; Vite production build succeeded (**101 modules**) and
  refreshed committed `dist`. FastAPI `TestClient` returned HTML 200 for `/`,
  `/app/accounts`, and the legacy `/ledger/dashboard`. Playwright against a
  fresh migrated temp SQLite database verified API-connected loading/empty
  states; pointer navigation through Dashboard/Profiles/Accounts/Categories/
  Settings; brand navigation; theme light → dark → light; profile-create entry,
  a real profile creation, switcher open, and Escape close; and legacy
  `/aurora/dashboard` redirect to `/app/dashboard`. Keyboard tab order covered
  skip link, brand, all five nav links, theme, and profile control. Rendered
  light/dark checks passed at **1440×900, 768×900, and 375×812** with no document
  horizontal overflow; all five mobile tabs remain visible, top controls are
  44×44px minimum, and reduced-motion media emulation reduced transitions to
  0.01ms. Final `rg` found no UI-directions/prototype/sample/Meridian runtime
  strings; `git diff --check -- apps/web` passed (line-ending warnings only).
- Decisions: Ledger's dark terminal-style top rail and sky-blue accent are the
  sole visual direction. Transaction UI should extend the absolute `/app/*`
  routes and `--lg-*` tokens, use tabular figures, and remain API-only.
- Blockers/risks: The required `ui-ux-pro-max` skill was read and applied, but
  its documented `search.py` is missing, so embedded guidance drove the checks.
  The Playwright CLI's `npx` prerequisite was unavailable; rendered QA used the
  installed persistent Playwright runtime with system Edge instead. No pnpm
  lock/workspace artifacts remain.
- Handoff: FE-07 can add the transactions nav route/workspace after BE-11 is
  done, preserving the Ledger shell, absolute `/app/*` routes, `--lg-*` tokens,
  44px targets, focus visibility, themes, responsiveness, and reduced motion.

### 2026-07-16 — BE-10 — Codex / be10_transaction_services

- Status: `DONE`
- Scope: `apps/api/app/services/transactions.py`, service exports,
  transaction model/schema/rules corrections, Alembic revision 0005,
  `tests/test_transaction_{rules,services,migration}.py`, and this workboard.
- Work: Added profile-scoped transaction create/get/list/update services with
  account, direct-or-split category, type, inclusive date, included-state, and
  merchant/raw-description/notes/tag search filters. Added exact split replace/
  clear and case-insensitive reusable tag management, soft delete/restore, and
  uniform non-disclosing cross-profile lookup behavior. Services flush without
  commit/rollback. Corrected the accepted transaction contract: nonzero signed
  cents use debit-positive/credit-negative convention; only purchases default
  included, cash advances alone may opt in, excluded categories force exclusion,
  and only included purchases may carry two-or-more same-sign exact-sum splits.
  Added editable `raw_description` with required-null protection. Added
  `transfer` to model/schema/storage through revision 0005; downgrade maps live
  transfers deterministically to excluded `payment` rows before restoring the
  old CHECK constraint.
- Verification: focused transaction/rule/migration suite **13 passed**; full
  backend suite **94 passed**; `ruff check app tests alembic` passed. Alembic
  coverage upgrades to head, persists a transfer, downgrades to 0004, and
  verifies its deterministic `payment` mapping. `graphify update .` initially
  hit the repository's protected pytest-temp ACL, then succeeded with approved
  access: **1,224 nodes, 1,934 edges, 135 communities**. The initial focused
  pytest attempt likewise hit that existing ACL; reruns used the system temp
  root and passed.
- Decisions: Empty splits clear the allocation; non-empty splits require at
  least two rows. Explicit `included_in_spending=True` is valid for purchases
  and cash advances only; explicit false remains available for exclusion.
  Collection filters using a foreign-profile account/category ID return an
  empty scoped result, while addressed transaction/split/tag operations return
  the identical `transaction not found` used for missing IDs.
- Blockers/risks: none.
- Handoff: BE-11 is `READY`. Build nested transaction routes against the public
  exports in `app.services`; map `ResourceNotFoundError` to uniform 404 and
  `InvalidUpdateError`/`SplitSumError` to field-readable 422 responses, while
  preserving request-owned commit/rollback boundaries.

### 2026-07-16 09:45 EDT — FE-LEDGER-01 review fixes — Codex / ledger_consolidation

- Status: `IN PROGRESS`
- Scope: Ledger semantic colour tokens, profile-switcher keyboard behavior,
  category icon types/components/rendering, frontend tests, `apps/web/dist/`,
  and the FE-LEDGER-01 row/log only.
- Work: Reopened the task for review blockers: light-theme accent/avatar
  contrast, disclosure focus return and keyboard semantics, and structural
  category emoji replacement with SVG icons.
- Verification: pending focused contrast calculations, keyboard/browser checks,
  typecheck, tests, build, refreshed committed `dist`, and diff checks.
- Decisions: preserve API category `icon` strings while normalizing legacy
  values to a production SVG icon vocabulary at the presentation boundary.
- Blockers/risks: none.
- Handoff: close all review findings, return FE-LEDGER-01 to `DONE`, and publish
  exact verification results.

### 2026-07-16 09:43 EDT — BE-11 — Codex / be11_contract_audit

- Status: `IN PROGRESS`
- Scope: transaction API schemas/exports, `apps/api/app/routers/transactions.py`,
  `apps/api/app/main.py`, focused transaction API tests, and this workboard.
- Work: Claim typed profile-nested transaction routes, static bulk
  categorize/inclusion actions, reachable split/tag replacement, soft-delete/
  restore lifecycle responses, and uniform 404/422 error mapping.
- Verification: pending focused/full backend tests, Ruff, migration/OpenAPI
  checks, `git diff --check`, and Graphify refresh.
- Decisions: Preserve BE-10's transaction-neutral service boundaries and the
  request-owned transaction for atomic bulk behavior; expose exact affected
  counts and reject empty, duplicate, or over-500 bulk ID lists.
- Blockers/risks: none.
- Handoff: Implement and verify BE-11, then unblock FE-07.

### 2026-07-16 09:51 EDT — BE-11 — Codex / be11_contract_audit

- Status: `DONE`
- Scope: `apps/api/app/schemas/transaction.py`, schema exports,
  `apps/api/app/routers/transactions.py`, `apps/api/app/main.py`, transaction API
  tests, the profile/account OpenAPI assertion, and this workboard.
- Work: Added typed profile-nested transaction create/list/filter/get/update,
  soft-delete/restore, split replacement, tag replacement, and discriminated
  bulk categorize/spending-inclusion routes. Detail/list responses expose
  `deleted_at`; detail responses include splits/tags; lifecycle responses report
  explicit deleted state. Bulk requests reject empty, duplicate, non-positive,
  or over-500 ID lists, return an exact affected count, distinguish manual
  categorization from uncategorization, preflight profile scope, and remain
  atomic through the request-owned transaction. Added uniform `SplitSumError`
  422 mapping beside the existing non-disclosing 404/invalid-update handlers.
- Verification: focused transaction API suite **10 passed**; full backend suite
  **104 passed**; `ruff check app tests alembic` passed. Fresh migration
  `upgrade head` reported revision 0005, then `downgrade 0004` and `upgrade head`
  passed. OpenAPI exposes all six transaction path groups and the `/bulk` body
  has the expected discriminator/oneOf mapping. `git diff --check` passed
  (line-ending warnings only). Graphify refresh initially hit the known
  protected pytest-temp ACL, then succeeded with approved access: **1,297
  nodes, 2,113 edges, 145 communities**.
- Decisions: `PATCH /bulk` uses `categorize` and `set_spending_inclusion`
  actions; null category sets `uncategorized`, while a real category sets
  `manual`. Bulk exclusion requires a readable reason and re-inclusion clears
  it. Tag replacement deterministically case-insensitive-deduplicates via the
  BE-10 service. Empty split/tag lists clear; non-empty splits retain BE-10's
  two-or-more, same-sign, exact-cent invariant. Transaction `DELETE` is a soft
  lifecycle action and therefore does not weaken the no-hard-delete contract
  for profiles/accounts.
- Blockers/risks: none.
- Handoff: FE-07 is `READY`. Mirror the verified nested OpenAPI types, consume
  `deleted_at`/detail splits/tags and bulk `updated_count`, and implement the
  API-only Ledger transaction workspace from the prepared FE-07 handoff.

### 2026-07-16 09:54 EDT — FE-LEDGER-01 review fixes — Codex / ledger_consolidation

- Status: `DONE`
- Scope: Ledger semantic colour tokens, `ProfileSwitcher`, category icon
  types/rendering, narrow/mobile responsive hardening, focused frontend test,
  `apps/web/dist/`, and this workboard.
- Work: Closed the Ledger accessibility review. Darkened the light semantic
  accent to `#0369a1`, added theme-specific on-accent foregrounds, and made
  profile avatars/buttons use contrast-safe pairs. Replaced category emoji
  choices and rendering with a consistent 17-name inline SVG system while
  normalizing legacy API icon strings at the presentation boundary. Converted
  the profile popup to a standard disclosure group with normal Tab navigation;
  every close path now moves focus intentionally (Escape, selection, and
  backdrop → trigger; Manage profiles → route main). Hardened 16px mobile text/
  inputs, internal tab scrolling, and narrow layouts for 200% zoom.
- Verification: computed light ratios: accent/white **5.93:1**, accent/app
  background **5.27:1**, accent/14%-tint **4.83:1**, white/accent **5.93:1**,
  and white/accent-2 **7.56:1**. Rendered Playwright checks confirmed the avatar
  pair at **5.93:1**, **13/13** seeded category rows render SVGs with no emoji
  text, Escape/selection/backdrop restore trigger focus, and Manage profiles
  moves focus to `#main-content`. At 375px there is no page overflow; simulated
  200% zoom (188 CSS px) also has **no document horizontal overflow**, while the
  360px tab row scrolls inside its 173px container. Mobile body/input text is
  16px. Final bundled-runtime `tsc --noEmit` passed; Vitest **4 files, 11 tests
  passed** (including the disclosure focus regression test); Vite built **102
  modules** and refreshed committed `dist`. Emoji search across category source
  and `dist` returned no matches; scoped `git diff --check` passed with only
  line-ending warnings.
- Decisions: Legacy emoji values remain accepted as API data through numeric
  code-point aliases, but no production structural control or rendered category
  icon uses emoji. The simpler disclosure pattern avoids claiming application-
  menu keyboard semantics for ordinary profile navigation.
- Blockers/risks: none.
- Handoff: FE-07 may now extend the settled Ledger AppShell/styles. Preserve the
  verified contrast pairs, SVG icon language, intentional focus movement,
  16px mobile controls, internally scrollable tabs, and 200%-zoom containment.

### 2026-07-16 09:56 EDT — FE-07 — Codex / be11_contract_audit

- Status: `IN PROGRESS`
- Scope: `apps/web/src/features/transactions/`, minimal Ledger AppShell route/
  navigation wiring, API client PUT/DELETE support, TanStack Table dependency,
  frontend tests, committed `apps/web/dist/`, and this workboard.
- Work: Build the API-only transaction workspace for the active profile with
  search/filters, semantic paginated table and responsive cards, create/edit,
  inline category, inclusion state, detail split/tag editing, bulk actions,
  soft-delete trash/restore, and complete request states.
- Verification: pending typecheck, Vitest, production build, rendered desktop/
  tablet/mobile and 200%-zoom checks, light/dark contrast, keyboard/focus flow,
  reduced motion, API-only/no-sample audit, diff check, and Graphify refresh.
- Decisions: Preserve the settled Ledger semantic tokens, SVG icon language,
  44px targets, intentional focus movement, and integer-cent API boundaries.
  The required `ui-ux-pro-max` search script is still absent, so the fully read
  skill's embedded design/accessibility rules drive implementation and QA.
- Blockers/risks: none.
- Handoff: Implement and verify FE-07, then unblock QA-03.

### 2026-07-16 10:33 EDT — FE-07 — Codex / be11_contract_audit

- Status: `DONE`
- Scope: `apps/web/src/features/transactions/`, Ledger AppShell transaction nav/
  route, API client PUT/DELETE support, `@tanstack/react-table` dependency and
  lockfile, focused frontend tests, committed `apps/web/dist/`, and this board.
- Work: Delivered the active-profile API-only Ledger workspace with debounced
  search and composable account/category/type/date/inclusion/trash filters;
  URL-persisted filters, sort, and pagination; sortable semantic desktop table
  and responsive cards; inline category editing; explicit included/excluded
  text; exact-cent create/edit; split and tag detail editing; confirmed bulk
  categorize/include/exclude with affected counts and type-policy preflight;
  soft-delete trash/restore; and complete loading, empty, error, retry, and no-
  profile states. Profile switches clear every owned transient state and never
  retain previous-profile transaction placeholder data.
- Verification: bundled Node TypeScript check passed; final Vitest run passed
  **8 files, 23 tests**, including the **3/3** focused modal/sign regressions;
  Vite production build passed **113 modules** and refreshed committed assets
  `index-CXL_zMtY.css` (26.87 kB) and `index-BmdDDuA2.js` (331.55 kB). Fresh
  migrated SQLite + latest uvicorn on loopback exposed all **6** transaction
  OpenAPI path groups. Direct live lifecycle verified two transactions, two
  exact splits, two tags, bulk exact count, delete/trash, and restore; built
  `/app/transactions` plus hashed assets returned 200 and contained no sample-
  data runtime. Independent rendered QA on the latest build passed real UI
  create/edit, exact two-way split, tag save, atomic bulk categorize, soft
  delete, trash filter, restore, light/dark toggle, keyboard Add/Escape focus
  return, and Detail→Edit modal focus. Semantic desktop table and mobile cards
  had no document overflow at **1440×900, 768×900, 375×812**, or simulated
  **200% zoom (720×450)**; reduced-motion transitions measured **0.00001s**;
  browser console/page errors were zero. Scoped `git diff --check` passed with
  line-ending warnings only. Final Graphify code refresh succeeded: **1,384
  nodes, 2,349 edges, 142 communities**.
- Decisions: Applied the fully read `ui-ux-pro-max` embedded rules because its
  documented `search.py` remains absent: semantic theme tokens, contrast-safe
  text-plus-state labels, SVG icon language, ≥44px targets, labelled controls,
  modal traps/restoration, responsive containment, and reduced motion. Debit is
  positive and credit negative at the form boundary; only purchases and cash
  advances can be bulk-included; all amounts remain exact safe integer cents.
- Blockers/risks: none. Documentation changes in this final log may be newer
  than Graphify's semantic document extraction; code relationships are current.
- Handoff: QA-03 is `READY` for the complete backend/frontend transaction-slice
  validation pass. Do not reintroduce sample transactions or comparison UI.

### 2026-07-16 10:11 EDT — BE-10/BE-11 contract correction — Codex / ledger_consolidation

- Status: `IN PROGRESS`
- Scope: `apps/api/app/schemas/transaction.py`, schema exports if required,
  focused transaction API tests, and this workboard; FE-07 files and ownership
  remain untouched.
- Work: Add one centrally defined signed JavaScript-safe integer-cent bound to
  every transaction and split API input/output schema boundary so JSON clients
  cannot silently round persisted cent amounts.
- Verification: pending focused/full backend pytest, Ruff, diff check, and
  Graphify refresh.
- Decisions: Keep the database `BigInteger` representation and all existing
  nonzero, direction/sign, spending-inclusion, and exact split-sum rules. This
  correction narrows only the interoperable HTTP amount range to
  `±Number.MAX_SAFE_INTEGER`.
- Blockers/risks: none.
- Handoff: Verify rejection immediately outside both bounds plus valid boundary
  round-trips, then record the completed correction without changing FE-07.

### 2026-07-16 10:15 EDT — BE-10/BE-11 contract correction — Codex / ledger_consolidation

- Status: `DONE`
- Scope: `apps/api/app/schemas/transaction.py`,
  `apps/api/tests/test_transaction_api.py`, this workboard, and the generated
  Graphify refresh; no FE-07 file or status was changed.
- Work: Added the shared `MAX_SAFE_CENTS = 2^53 - 1` and constrained
  `CentAmount` type to transaction create/update/read and split input/read
  boundaries. OpenAPI now publishes the signed minimum and maximum, preventing
  JavaScript clients from silently rounding cent values while SQLite continues
  to use `BigInteger`.
- Verification: focused transaction API suite **13 passed**; full backend suite
  **107 passed**; `ruff check app tests alembic` passed; scoped
  `git diff --check` passed with line-ending warnings only. Tests reject both
  `MAX_SAFE_CENTS + 1` and `-MAX_SAFE_CENTS - 1` on create, update, and split
  replacement, and verify exact positive/negative boundary round-trips plus a
  maximum-total split. Graphify's sandboxed refresh hit the known protected
  pytest-temp ACL; the approved rerun succeeded with **1,378 nodes, 2,335
  edges, and 139 communities**.
- Decisions: No database migration or service-rule change is needed. Existing
  nonzero/sign, spending-inclusion, and exact split-sum validation remains
  authoritative inside the narrowed interoperable range.
- Blockers/risks: none.
- Handoff: FE-07 can rely on the generated OpenAPI bound or mirror
  `Number.MAX_SAFE_INTEGER` at its amount-entry boundary; QA-03 should retain
  the new backend boundary tests in its full regression run.

### 2026-07-16 10:36 EDT — QA-03 — Codex / ledger_review

- Status: `IN PROGRESS`
- Scope: Independent cross-app validation only; no feature edits unless a transaction-slice defect is found; this workboard for claim and handoff.
- Work: Validate fresh migration upgrade/current/downgrade/re-upgrade, full backend/frontend gates, transaction OpenAPI, exact-cent/split, inclusion, atomic bulk, isolation, soft delete/restore, committed dist, retired sample/comparison runtime, and Graphify health.
- Verification: pending.
- Decisions: rely on prior rendered/live records only after confirming the current final asset hashes; independently rerun non-rendered gates.
- Blockers/risks: none.
- Handoff: mark `DONE` only if all checks pass; otherwise reopen the owning task.

### 2026-07-16 10:41 EDT — QA-03 — Codex / ledger_review

- Status: `DONE`
- Scope: Independent validation of the complete transactions slice; no feature implementation files were changed. This workboard was updated for task and milestone status.
- Work: Validated the final backend, frontend, generated dist, OpenAPI contract, transaction domain behavior, retired runtime, prior live/rendered evidence, and Graphify output. M3 and M4 now meet their recorded exit conditions and are marked `DONE`.
- Verification: A fresh disposable SQLite database upgraded from base to `0005_transaction_transfer_type` head, reported current, downgraded to `0004_transaction_models`, reported current, and re-upgraded to head successfully. Full backend pytest passed **107/107** using a workspace-local temp root after the sandbox hit the known protected system pytest-temp ACL; focused transaction rules/services/API/migration tests passed **26/26**; `ruff check app tests alembic` passed. OpenAPI exposes all **6** transaction path groups and exact-cent bounds of **±9,007,199,254,740,991** on create, update, read, and split schemas. The focused tests cover exact split sums and mismatch rejection, sign/direction and default-inclusion policy, filters, atomic bulk failure/counts, profile isolation, safe-cent rejection and round-trip boundaries, soft delete/trash/restore, tags, and transfer migration. Frontend TypeScript passed; Vitest passed **8 files / 23 tests**; Vite built **113 modules** and reproduced `index-CXL_zMtY.css` (**26.87 kB**) plus `index-BmdDDuA2.js` (**331.55 kB**). `dist/index.html` references both existing hashed assets; scoped `git diff --check` passed with line-ending warnings only. Static runtime scans found no sample/comparison files or text in `apps/web/src` or `apps/web/index.html`. The current asset hashes exactly match FE-07's recorded live lifecycle and independent rendered UI evidence, including Add/Edit, split/tag, bulk, delete/trash/restore, focus, responsive, theme, reduced-motion, and zero browser errors. Graphify reports **1,384 nodes, 2,349 edges, 142 communities, 0 dangling edges**, **34 hyperedges**, and **352 transaction-related nodes**; the focused transaction query resolves current services and acceptance tests.
- Decisions: Accepted the prior live Playwright lifecycle and rendered UI review because they target the exact final asset hashes independently rebuilt here. Applied the fully read `ui-ux-pro-max` guidance to audit the recorded accessibility, interaction, responsive, and reduced-motion results; no UI defect was found. The initial system-temp pytest ACL error is environmental and was resolved by an isolated workspace-local `--basetemp`; it is not a product failure.
- Blockers/risks: none. The newly appended workboard record may be newer than Graphify's semantic document extraction; its code relationships match the validated final implementation.
- Handoff: Transactions slice validation is complete. No BE-10, BE-11, or FE-07 task needs reopening; proceed to the next dependency-ready Ledger feature without restoring comparison UI or sample transactions.

### 2026-07-16 10:44 EDT — Stage 3 board expansion — Codex / ledger_consolidation

- Status: `DONE`
- Scope: planning-only update to this workboard; no implementation files or
  task claims.
- Work: Replaced the duplicated import backlog entries with dependency-ordered
  BE-12 through QA-04 rows for persistence/contracts, safe extraction, the TD
  parser, preview/commit services, typed APIs, the Ledger import workflow, and
  the Stage 3 acceptance gate. Updated the current phase, dependency map, and
  milestones after QA-03.
- Verification: Confirmed QA-03 remains `DONE`; BE-12 and BE-13 are the only
  `READY` Stage 3 tasks; BE-14, BE-15, BE-16, FE-08, and QA-04 remain `BLOCKED`
  on their recorded dependencies. Reviewed the new rows for explicit profile
  isolation, integer-cent reconciliation, atomicity, temporary-file cleanup,
  log redaction, frontend `ui-ux-pro-max` use, and the prohibition on raw PDF or
  full extracted-text persistence.
- Decisions: BE-12 owns migration/import persistence files while BE-13/BE-14
  own extraction/parser/fixture files, allowing safe parallel work. BE-15 is
  the sole staging-to-final-transaction convergence point. M5 is open until
  QA-04 validates the complete TD import flow.
- Blockers/risks: Documentation-only changes may leave Graphify's semantic
  document extraction stale; source-code graph relationships are unaffected.
- Handoff: Two agents may independently claim BE-12 and BE-13. No later Stage 3
  task should be claimed until its direct dependencies are `DONE`.

### 2026-07-16 10:48 EDT — BE-13 — Codex / be11_contract_audit

- Status: `IN PROGRESS`
- Scope: `apps/api/app/importing/`, `apps/api/app/parsers/base.py` and parser
  exports, `apps/api/requirements.txt`, focused importing tests, and this
  workboard only.
- Work: Claim safe, typed statement-parser contracts, streamed document
  validation/extraction, exact reconciliation and exchange-rate primitives,
  and privacy-preserving fingerprints.
- Verification: pending focused/full pytest, Ruff, cleanup/cancellation and
  privacy regression checks, `git diff --check`, and Graphify refresh.
- Decisions: Keep BE-12 persistence/models/schemas/migration entirely outside
  this task. Raw PDF bytes and full extracted text remain ephemeral; client
  paths are never trusted or logged.
- Blockers/risks: none.
- Handoff: Complete BE-13 acceptance, then make BE-14 `READY` only if every
  safety and verification gate passes.

### 2026-07-16 — BE-12 — Codex / be10_transaction_services

- Status: `IN PROGRESS`
- Scope: import ORM models and Pydantic persistence schemas; model/schema
  exports; Profile/Account/Transaction import relationships; Alembic revision
  0006; focused model/schema/migration tests; this workboard.
- Work: Claim profile-isolated import-batch, staging, warning, and final-link
  persistence contracts with exact integer-cent and fixed-precision foreign-
  exchange fields, indexed deduplication keys, and privacy-safe column surfaces.
- Verification: pending focused/full pytest, 0005↔0006 migration cycles, Ruff,
  Graphify refresh, schema privacy inspection, and `git diff --check`.
- Decisions: BE-12 owns persistence only. Do not add document extraction,
  parsers, reconciliation algorithms, temporary-file handling, preview/commit
  services, routers, or fixtures owned by BE-13 through BE-16.
- Blockers/risks: none.
- Handoff: Complete and verify BE-12, then unblock the BE-12 side of BE-15.

### 2026-07-16 11:07 EDT — BE-12 — Codex / be10_transaction_services

- Status: `DONE`
- Scope: Added profile-isolated import batch, staged transaction, warning, and
  final transaction-link models; persistence schemas and exports; profile,
  account, and transaction relationships; transaction import/foreign-currency
  provenance; reversible Alembic revision 0006; focused regression tests.
- Work: Enforced same-profile account/batch/staged/final ownership with
  composite foreign keys; indexed file hash, logical statement key, and
  profile/account fingerprints; retained only sanitized filenames and
  structured row/warning/cent summaries. Added exact `NUMERIC(18,8)` exchange
  rates and JavaScript-safe integer-cent constraints. Revision 0006 snapshots
  and restores transaction splits/tags around SQLite table rebuilds so both
  upgrade and downgrade preserve existing ledger history.
- Verification: focused BE-12 suite `10 passed`; full API suite `142 passed`;
  Ruff passed; SQLAlchemy mapper configuration passed with `SAWarning` promoted
  to errors; 0005→0006→0005 preserved transactions, splits, and tags; schema
  privacy inspection passed; `git diff --check` passed with only existing line-
  ending warnings; `graphify update .` rebuilt 1,585 nodes / 2,752 edges.
- Decisions: Import persistence stores no PDF bytes, extracted page text,
  client paths, or full account numbers. Raw extraction remains ephemeral and
  stays in BE-13/BE-14 scope.
- Blockers/risks: none in BE-12. BE-15 remains blocked until BE-14 is complete;
  its BE-12 dependency is now satisfied.
- Handoff: BE-14 may consume these staging contracts; BE-15 may consume them
  once all of its remaining dependencies are complete.

### 2026-07-16 11:09 EDT — BE-13 — Codex / be11_contract_audit

- Status: `DONE`
- Scope: `apps/api/app/importing/`, the canonical parser base/exports,
  `apps/api/requirements.txt`, focused importing tests, and this workboard;
  BE-12 persistence files remained separately owned.
- Work: Added issuer-neutral typed parser detection/metadata/transaction/
  reconciliation contracts with strict runtime invariants and non-revealing
  representations; exact signed-cent reconciliation with one-cent tolerance;
  fixed eight-place positive finite Decimal exchange-rate parsing; streamed
  SHA-256; and caller-keyed HMAC-SHA256 statement/row fingerprints that retain
  deterministic occurrence indexes for legitimate repeated rows. Added strict
  extension, MIME, PDF-magic, byte, page, extracted-character, and processing-
  time limits; path-discarding filename sanitization with bidi/control removal
  and long-digit redaction; actionable malformed/scanned PDF errors; and logs
  restricted to generated document IDs and counts.
- Verification: focused importing suite **26 passed**; full API suite **142
  passed**; repository `ruff check app tests alembic` passed; `pip check` found
  no broken requirements; scoped `git diff --check` passed with line-ending
  warnings only. Real never-releasing child-process tests prove sync timeout and
  async cancellation complete within bounds, terminate/join/kill the worker,
  and leave no raw temp file. Independent privacy/security review and final
  re-review are clean. Final approved Graphify refresh reports **1,586 nodes,
  2,756 edges, and 167 communities**.
- Decisions: PDF traversal runs in a spawned, terminable process rather than a
  thread so compressed or malicious extraction is memory-isolated and can be
  killed on timeout/cancellation on Windows. Fingerprints require caller-owned
  local key material of at least 32 bytes; low-entropy transaction fields are
  never exposed through an unkeyed digest. Full extracted text remains
  ephemeral and is never logged or persisted.
- Blockers/risks: none. This final workboard entry may be newer than Graphify's
  semantic document extraction; final code relationships are current.
- Handoff: BE-14 is `READY` to implement the TD parser using only synthetic or
  redacted fixtures. It must provide occurrence indexes, pass a local HMAC key
  at fingerprint call sites, preserve exact cents/Decimal exchange rates, and
  never persist or log raw PDF/full extracted text.

### 2026-07-16 11:12 EDT — BE-14 — Codex / be11_contract_audit

- Status: `IN PROGRESS`
- Scope: `apps/api/app/parsers/td.py`, parser exports,
  `fixtures/statements/td/**`, `docs/parser-notes/td.md`, focused TD parser
  tests, and this workboard only.
- Work: Claim the versioned TD credit-card adapter and entirely synthetic PDF/
  canonical-output fixture matrix covering page sections, continuations,
  transaction types, exact money, occurrence indexing, and reconciliation.
- Verification: pending focused/full pytest, Ruff, synthetic-fixture privacy
  scan, unsupported/scanned-layout checks, `git diff --check`, independent
  review, and Graphify refresh.
- Decisions: No real or privately supplied statement content may enter the
  workspace. BE-14 consumes BE-13 contracts without changing persistence,
  import services, routes, or generic extraction primitives.
- Blockers/risks: none.
- Handoff: Complete and independently review the parser matrix; unblock BE-15
  only if all layout, reconciliation, privacy, and regression gates pass.

### 2026-07-16 11:13 EDT — BE-12 review corrections — Codex / be10_transaction_services

- Status: `IN PROGRESS`
- Scope: BE-12 import ORM ownership relationships and constraints, Alembic
  revision 0006, focused persistence/migration tests, and this workboard.
- Work: Reopen BE-12 for independent-review findings: bind every staged row to
  its owning batch's selected account; bind each imported transaction/link to
  the same profile and account as its batch; and make ORM profile deletion rely
  on database cascades without nulling non-null import ownership fields.
- Verification: pending database/ORM boundary regressions, focused/full pytest,
  migration cycle, Ruff, mapper warning gate, Graphify refresh, independent
  re-review, and `git diff --check`.
- Decisions: Enforce these invariants in database composite keys, not only in
  future BE-15 services. BE-15 stays `BLOCKED`; reopening BE-12 removes one
  satisfied dependency while BE-14 remains incomplete.
- Blockers/risks: none.
- Handoff: Correct and verify the persistence contract, then request a clean
  re-review before returning BE-12 to `DONE`.

### 2026-07-16 11:33 EDT — BE-12 review corrections — Codex / be10_transaction_services

- Status: `DONE`
- Scope: Corrected BE-12 import ownership relationships/constraints, revision
  0006, schema sanitization, persistence/migration regressions, and this board.
- Work: Enforced transaction profile/account ownership and exact batch-account
  ownership for staged/final imported rows with composite foreign keys. Import
  links now separately bind the current batch/staged row and the linked
  transaction's profile/account, allowing a prior-batch same-account duplicate
  while rejecting wrong-account/cross-profile targets. ORM account/batch
  relationships use `passive_deletes="all"` where database RESTRICT is
  authoritative; profile deletion cascades without nulling ownership fields.
  Revision 0006 normalizes legacy placeholder import IDs before DDL, preflights
  incompatible ownership before any schema mutation, rejects control/bidi
  filenames at schema and database boundaries, and restores split/tag backups
  with fail-closed inserts rather than lossy ignore semantics.
- Verification: final focused BE-12 suite **26 passed**; full API suite **172
  passed**; repository Ruff passed; SQLAlchemy mapper configuration passed with
  `SAWarning` promoted to errors. Migration tests cover 0005→0006→0005, exact
  split IDs/amounts/timestamps and tag associations, legacy import-ID
  normalization, no-partial-DDL failure/fix/retry, and composite FK/index
  inspection. `git diff --check` passed with existing line-ending warnings
  only. Final `graphify update .` completed with no topology delta after the
  preceding rebuild (**1,653 nodes / 2,965 edges**).
- Decisions: Current-batch provenance and duplicate-target ownership are
  distinct invariants: a duplicate audit link may target an earlier or manual
  transaction only when profile/account ownership matches the current batch.
- Blockers/risks: none. Independent reviewer `/root/ledger_consolidation`
  returned `CLEAN` after verifying all original P1/P2 findings and the final
  duplicate-link correction. This appended log may be newer than Graphify's
  semantic document extraction; code relationships are current.
- Handoff: BE-15 is now `READY`; consume these database-enforced ownership
  contracts without weakening them in preview/commit services.

### 2026-07-16 11:35 EDT — BE-13 availability regression correction — Codex / be11_contract_audit

- Status: `DONE`
- Scope: The existing never-releasing extraction-worker regression in
  `apps/api/tests/test_importing_primitives.py`; no extraction behavior changed.
- Work: Replaced a scheduler-sensitive sub-750ms assertion with a hard 2.5s
  availability bound that accommodates the documented one-second terminate/join
  cleanup deadline while retaining the decisive child-dead and temp-empty
  assertions.
- Verification: The isolated timeout regression passed; two sequential full
  backend suites passed **164/164** and **165/165** before concurrent BE-12
  corrections landed. The worker still terminates and leaves no statement file.
- Decisions: Test the documented bounded-cleanup contract rather than host
  scheduling luck. No production deadline or security guarantee was relaxed.
- Blockers/risks: none.
- Handoff: Keep the child-dead and temp-empty assertions alongside the hard time
  bound in future extraction availability tests.

### 2026-07-16 11:35 EDT — BE-14 — Codex / be11_contract_audit

- Status: `DONE`
- Scope: `apps/api/app/parsers/td.py`, parser exports, the synthetic
  `fixtures/statements/td/` corpus and generator, `docs/parser-notes/td.md`, TD
  parser tests, and this workboard.
- Work: Added the versioned, section-aware TD credit-card parser; exact signed-
  cent amount grammar; period-safe transaction/posting-date inference including
  cross-year leap days; post-continuation transaction classification; explicit
  multiline description and all-or-nothing foreign-currency continuations;
  deterministic occurrence indexes; and independent net, debit/credit,
  purchases, interest, fees, and credits reconciliation. Malformed comma
  grouping, incomplete/duplicate/conflicting foreign details, ambiguous rows,
  unsupported layouts, and image-only documents all fail closed. The parser
  consumes caller-owned HMAC boundaries and never owns or creates key material.
- Verification: Final focused TD suite passed **14/14**; independent TD plus
  importing review suite passed **40/40**; repository Ruff passed. Earlier
  sequential full backend gates passed **164/164**, **165/165**, and **166/166**.
  The post-review full run reached **168 passed** with only two failures in
  concurrently reopened BE-12 `ImportTransactionLink.account_id` tests; no
  BE-14 test failed. Deterministic regeneration left all **5** committed PDF/JSON
  artifacts byte-identical. Extracted-text/golden/privacy tests and static scans
  found no name, address, barcode, unmasked 12–19 digit identifier, or private
  statement data. Scoped `git diff --check` passed with line-ending warnings
  only. The final approved Graphify code refresh reported **1,656 nodes, 2,977
  edges, and 168 communities**.
- Decisions: Preserve issuer-specific section totals in a private metadata
  subtype so equal-and-opposite section errors cannot cancel without expanding
  the issuer-neutral persistence contract. Strict comma grouping and duplicate
  continuation rejection favor review over silent monetary reinterpretation.
- Blockers/risks: none in BE-14. Documentation appended after Graphify's code
  extraction may remain semantically stale. BE-12 is separately `IN PROGRESS`,
  so BE-15 remains `BLOCKED` despite completion of its BE-14 dependency.
- Handoff: BE-15 may consume the TD parser only after BE-12 returns to `DONE`.
  Independent adversarial re-review is clean for all four corrected findings:
  section cancellation, continuation classification, malformed comma grouping,
  and conflicting foreign continuations.

### 2026-07-16 11:39 EDT — BE-15 — Codex / be10_transaction_services

- Status: `IN PROGRESS`
- Scope: `apps/api/app/services/imports.py`, service exports, the minimal import-
  aware transaction-service extension, focused import-service tests, and this
  workboard only.
- Work: Claim profile/account-isolated preview staging, account suggestion and
  explicit selection, exact and overlap duplicate decisions, occurrence-aware
  fingerprints, and atomic/idempotent commit/cancel lifecycle services.
- Verification: pending focused/full 172+ pytest, Ruff, mapper/migration gates,
  privacy/log and rollback/cleanup regressions, `git diff --check`, independent
  adversarial review, and Graphify refresh.
- Decisions: Consume the completed BE-12/13/14 contracts without persisting raw
  PDF bytes or extracted page text. Services flush but do not own the caller's
  outer commit; commit failure isolation will be enforced within a savepoint.
- Blockers/risks: none.
- Handoff: Complete BE-15 and make BE-16 `READY` only after clean independent
  review and all verification gates pass.

### 2026-07-16 11:55 EDT — BE-15 — Codex / be10_transaction_services

- Status: `DONE`
- Scope: Added profile-isolated import preview/commit/cancel services and
  exports, a minimal canonical imported-transaction creator, focused service
  regressions, and the reviewed database fingerprint-claim correction in the
  Transaction model/Alembic 0006.
- Work: Preview now validates parser counts, exact cents/delta/status, and the
  one-cent product tolerance before persisting only canonical candidates and
  coded warnings. Profile-scoped writer claims serialize file/logical duplicate
  decisions; account suggestions remain advisory while selection is explicit
  and same-profile. Occurrence-aware HMAC fingerprints preserve repeated valid
  rows. Exact imported matches alone auto-link; ambiguous normalized overlaps
  become `needs_review`. Commit takes a database writer claim, rechecks exact
  matches, uses a partial unique fingerprint index as the final concurrency
  guard, retries unique races by linking the winner, and constructs its result
  inside the same savepoint. Structured failure results persist `failed` while
  leaving zero transactions/links. Commit is idempotent and writes `pdf_import`,
  import ID, source-row reference, foreign provenance, and audit links.
- Verification: focused import slice **68/68 passed**; final service/migration
  correction suite **17/17 passed**; final full backend suite **187/187 passed**;
  repository Ruff passed; mapper configuration passed with `SAWarning` promoted
  to errors; 0005↔0006 migration/inspection passed including the partial unique
  fingerprint index and child-history preservation; scoped `git diff --check`
  passed with line-ending warnings only. True concurrent-session tests prove
  two previews converge to original+blocked and two commits converge to one
  transaction plus two links. Cleanup runs for success, missing/cross-profile,
  cancel, and failure paths; privacy tests prove logs omit filename, page text,
  and descriptions. Final Graphify refresh rebuilt **1,724 nodes / 3,253 edges /
  169 communities**.
- Decisions: Failed commits return a structured `failure_code="commit_failed"`
  result instead of throwing after marking the batch, allowing the caller-owned
  request transaction to durably commit the terminal failed state. Logger
  failures are non-fatal and cannot alter ledger semantics. The partial unique
  index applies only to non-null fingerprints, so manual rows remain unaffected
  and legitimate repeated statement rows remain distinct through occurrence
  indexes.
- Blockers/risks: none. Independent adversarial re-review by
  `/root/ledger_consolidation` is `CLEAN` after the concurrency, atomic-result,
  durable-failure, cleanup, and reconciliation corrections. This final appended
  workboard record is newer than Graphify's semantic document extraction; its
  code relationships are current.
- Handoff: BE-16 is `READY`. Its router must map structured commit failures to a
  privacy-safe error response without raising past the request transaction, so
  the `failed` terminal state commits; preserve the service cleanup and profile-
  scoped conflict semantics.

### 2026-07-16 11:58 EDT — BE-16 — Codex / be10_transaction_services

- Status: `IN PROGRESS`
- Scope: `apps/api/app/routers/imports.py`, router exports, `app/main.py`, a
  pre-multipart import-body limit middleware, upload/fingerprint-key
  configuration, typed import API schemas, focused API/OpenAPI tests, and this
  workboard. The middleware is a recorded acceptance-driven expansion needed to
  enforce the configured limit before Starlette spools an unbounded upload.
- Work: Claim profile-nested preview/get/commit/cancel endpoints for one TD PDF,
  with bounded extraction, structured privacy-safe responses, uniform scoped
  errors, durable structured commit failure mapping, and cleanup guarantees.
- Verification: pending focused/full backend pytest, Ruff, OpenAPI/privacy/
  upload-boundary tests, migration/mapper gates, `git diff --check`, independent
  adversarial review, and Graphify refresh.
- Decisions: Preserve BE-15's request-owned transaction contract: a structured
  `commit_failed` result will be returned as a response without raising through
  the session dependency, so the terminal `failed` state is committed.
- Blockers/risks: none.
- Handoff: Complete BE-16 and make FE-08 `READY` only after every acceptance
  gate and independent review pass.

### 2026-07-16 — FE-MERIDIAN-01 claimed

- Owner: Codex / `ledger_consolidation`
- Scope: production AppShell and current API-backed feature styles/copy,
  committed frontend distribution, ADR 0002, and current workboard direction.
- Work: Claimed the ready frontend task after the product owner's direct
  decision to supersede Ledger styling with Meridian. The existing comparison
  harness, prototype runtimes, and sample data remain retired.
- Decisions: Preserve every live API route and use the existing `--lg-*`
  feature-token names as temporary compatibility aliases to one Meridian token
  system; do not restore the deleted Meridian prototype.
- Verification: Read this workboard in full; queried Graphify before source
  inspection; read `ui-ux-pro-max` in full. Its optional `scripts/search.py`
  helper is absent, so embedded accessibility, responsive, theme, and motion
  guidance will be applied directly and recorded at completion.

### 2026-07-16 12:08 EDT — FE-MERIDIAN-01 — Codex / ledger_consolidation

- Status: `NEEDS REVIEW`
- Scope: Production AppShell, current dashboard/settings/transaction copy,
  shared feature-token compatibility, frontend metadata/distribution, ADR 0002,
  current workboard direction, and Graphify refresh.
- Work: Superseded Ledger's terminal-style chrome with one Meridian blue-violet
  system across the existing API-backed application. Added rounded translucent
  navigation, softer live-data surfaces, theme-aware semantic tokens, and a
  working Dashboard-to-Transactions action; retained current profile, account,
  category, transaction, theme, health, and navigation behavior. Updated the
  product decision without restoring the comparison harness, prototype routes,
  or synthetic runtime data.
- Verification: `npm run typecheck` passed; Vitest **8 files / 23 tests passed**;
  `npm run build` passed (**113 modules**) and refreshed `dist`; static runtime
  scan found no comparison/prototype/sample imports; scoped `git diff --check`
  passed with line-ending warnings only. The `ui-ux-pro-max` checks confirm
  visible 3px focus, semantic controls/SVG icons, ≥44px interactive targets,
  375/520/768/1000 responsive breakpoints, mobile 16px form text, reduced-
  motion override, and theme-separated tokens. Computed foreground contrast is
  **5.09:1–16.83:1** for core light/dark text and primary actions. Graphify
  refreshed to **1,790 nodes / 3,397 edges / 171 communities**.
- Decisions: Existing `--lg-*` feature variables remain as compatibility aliases
  to Meridian semantic values until feature CSS can be mechanically renamed;
  no Ledger palette or styling remains behind those names.
- Blockers/risks: The required in-app rendered QA at 375/768/1440, 200% zoom,
  light/dark, focus, and reduced motion could not run because the browser runtime
  returned zero available browser targets. Source checks passed, but this task
  cannot honestly be marked `DONE` until that visual gate is completed. This
  final workboard entry is newer than Graphify's semantic documentation pass;
  the refreshed code relationships are current.
- Handoff: Open the built app in an available in-app browser, render Dashboard
  and Transactions at 375/768/1440 in light/dark, verify keyboard focus and 200%
  zoom without horizontal page overflow, and then move FE-MERIDIAN-01 to `DONE`.

### 2026-07-16 12:14 EDT — FE-MERIDIAN-01 rendered acceptance — Codex / root

- Status: `DONE`
- Scope: Rendered acceptance of the built Meridian production application; no
  source changes beyond this task-status update.
- Work: Closed the remaining visual gate against the refreshed production
  distribution while preserving the API-backed routes and retired prototype/
  sample-data boundary.
- Verification: Local Edge/Playwright rendered **375/768/1440** in both light
  and dark themes with the correct Meridian title/brand, no page-level
  horizontal overflow, and zero visible controls undersized in both dimensions.
  At 200% CSS zoom there was no horizontal page overflow. Reduced motion
  computed to **0.00001s**; the first Tab reached the visibly outlined “Skip to
  content” link; “View transactions” navigated to `/app/transactions`.
  Screenshots and JSON evidence are in ignored `output/playwright/meridian-*`.
- Decisions: FE-MERIDIAN-01 meets its full acceptance contract; the production
  UI is Meridian and the old Meridian prototype remains retired.
- Blockers/risks: none.
- Handoff: Build new frontend features against the live Meridian production
  shell and semantic tokens; do not restore comparison or sample-data routes.

### 2026-07-16 12:16 EDT — BE-16 — Codex / be10_transaction_services

- Status: `DONE`
- Scope: Added the typed profile-nested import routes, safe response schemas,
  upload and extraction configuration, persistent fingerprint-key handling,
  pre-parser request-body limiting middleware, multipart dependency, focused
  API tests, and this workboard handoff. A narrow BE-15 duplicate-query
  correction permits a cancelled original statement to be retried even when a
  blocked-duplicate audit attempt exists.
- Work: Implemented preview, detail, commit, and cancel endpoints for one TD PDF
  per preview. Uploads are bounded before multipart completion, always closed,
  and processed through the BE-15 services. Duplicate preview attempts persist
  their reference before returning `409`; injected commit failures return a
  structured `500` without rolling back the durable failed import state.
  Responses omit file hashes, logical keys, fingerprints, raw PDF content, and
  extracted text. Error mappings cover `413`, `415`, readable `422`, `409`,
  uniform profile-scoped `404`, and privacy-safe `500` responses.
- Verification: Focused import API **9/9**, API/service slice **24/24**, and full
  backend **196/196** passed. Ruff, `pip check`, mapper warnings-as-errors,
  OpenAPI four-path/status/404 schema checks, migration tests, and scoped diff
  checks passed. Lifecycle/privacy, malicious filename, temp cleanup, rollback,
  duplicate/cancel/idempotence, and cross-profile isolation checks passed. The
  ASGI limiter preserves CORS and does not consume the final chunk after the cap.
  Windows binary exclusive key writes passed a 64-key stress check. Final
  independent review: **CLEAN/APPROVE**. Graphify refreshed to **1,815 nodes /
  3,435 edges / 175 communities**.
- Decisions: The maximum request envelope is the configured file limit plus a
  configurable 64 KiB multipart allowance; extraction limits remain exact.
  The fingerprint key is persisted beside the database by default and is never
  logged. Structured commit-failure responses are returned inside the request
  transaction so the failed lifecycle state commits.
- Blockers/risks: none. This documentation entry is newer than the semantic
  graph refresh; the AST-derived code graph is current.
- Handoff: `FE-08` is `READY`. Submit multipart fields `statement` and
  `account_id`; handle `409`, `413`, `415`, `422`, and structured `500`; require
  explicit acknowledgement for a needs-review commit; clear transient file
  state after cancel or commit. Coordinate minimal AppShell changes with the
  completed Meridian restyle and apply the mandatory `ui-ux-pro-max` workflow.

### 2026-07-16 12:25 EDT — FE-08 — Codex / ledger_consolidation

- Status: `IN PROGRESS`
- Scope: `apps/web/src/features/imports/**`, focused frontend API/component
  tests, minimal Meridian AppShell route/top-action styles, committed `dist`,
  Graphify refresh, and this workboard.
- Work: Claimed the now-ready Meridian statement-import workflow against the
  completed BE-16 contract. Implement one transient browser-memory PDF flow from
  select/drop through preview, review acknowledgement, commit/cancel, and a
  Transactions success handoff.
- Verification: pending typecheck, Vitest, build/dist, API error-contract tests,
  transient-file persistence scan, rendered 375/768/1440 light/dark/focus/zoom/
  reduced-motion checks, independent review, diff check, and Graphify refresh.
- Decisions: Submit only multipart `statement` + `account_id`; never place File,
  PDF bytes, or preview data in localStorage, IndexedDB, fixtures, or sample
  runtime modules. Clear File state after cancel and successful commit.
- Blockers/risks: `ui-ux-pro-max` was reread in full and its embedded rules are
  active, but the required optional `scripts/search.py` remains absent.
- Handoff: Complete FE-08 and seek independent review before moving it to DONE.

### 2026-07-16 12:30 EDT — FE-08 — Codex / ledger_consolidation

- Status: `NEEDS REVIEW`
- Scope: Added the Meridian Import Statement route and top action, typed import
  API/client contract, transient PDF workflow, focused tests, refreshed frontend
  distribution, Graphify output, and this handoff.
- Work: The top Import action now opens `/app/imports`. The profile-scoped flow
  accepts one selected/dropped PDF plus an active account, previews the live
  backend response, displays issuer suggestion, type counts, reconciliation,
  warnings, candidate/duplicate states, gates `needs_review` commits behind an
  explicit acknowledgement, supports cancel, and links successful commits to
  Transactions. Multipart contains only `statement` and `account_id`. Structured
  `409`, `413`, `415`, `422`, and terminal `500` outcomes receive actionable UI;
  blocked duplicates are retrieved as cancellable previews. `File` exists only
  in React state and is cleared after cancel, successful commit, profile change,
  and terminal failed commit; no file/preview persistence or sample runtime data
  was added.
- Verification: `npm run typecheck` passed; focused import/client **18/18** and
  full frontend **10 files / 34 tests** passed. Tests cover exact multipart
  fields, blocked `409` recovery, `413`/`415`/`422` guidance, structured `500`
  metadata and terminal cleanup, cancel/commit cleanup, acknowledgement, success
  link, and actual focus after async mounted transitions. `npm run build` passed
  (**116 modules**) and refreshed `dist`; scoped `git diff --check` passed with
  line-ending warnings only. Graphify refreshed to **1,858 nodes / 3,517 edges /
  182 communities**.
- UI/UX skill checks: `ui-ux-pro-max` was read in full; because its optional
  search helper is absent, its embedded rules guided the implementation. Source
  checks confirm semantic labels/alerts/status, keyboard-native controls,
  state-driven visible focus, SVG rather than emoji action icons, ≥44px action
  targets, mobile 16px select text, breakpoints at 1000/768/520, Meridian semantic
  light/dark tokens, and the existing global reduced-motion override. The File
  target is also a full-card label for pointer and touch use.
- Decisions: A persisted duplicate `409` is converted into its safe structured
  detail so the user can inspect and cancel it. A durable failed commit is
  terminal and cannot be cancelled by the backend, so the client releases the
  File/preview and preserves a focused diagnostic with retry guidance.
- Blockers/risks: Required rendered 375/768/1440 light/dark, 200%-zoom, focus,
  reduced-motion, and top-navigation acceptance remains with root's local
  Edge/Playwright path because this agent has no in-app browser target. An
  independent read-only reviewer is active; neither gate has been pre-claimed.
- Handoff: Root performs rendered acceptance and independent review returns
  CLEAN/APPROVE; then move FE-08 to `DONE` and unblock QA-04.

### 2026-07-16 12:33 EDT — FE-08 rendered acceptance — Codex / root

- Status: `NEEDS REVIEW`
- Scope: Rendered acceptance of the built Meridian Import Statement workflow;
  no source changes beyond recording this evidence.
- Work: Exercised the top Import navigation and complete select-PDF, preview,
  needs-review acknowledgement, commit-success, and Transactions handoff using
  mocked responses that match the live BE-16 wire contract.
- Verification: Local Edge/Playwright passed **375/768/1440** in light and dark
  with no page-level horizontal overflow. The top Import action navigated to
  `/app/imports`; keyboard focus was visibly outlined; preview and success
  headings received focus after async transitions. Commit remained disabled
  until acknowledgement and then rendered a three-created success result. At
  200% CSS zoom there was no page overflow; reduced motion computed to
  **0.00001s**. The only 1×1 control was the intentionally visually hidden
  native file input whose associated drop-label target is large. Mobile, dark
  tablet, full-preview, success, and zoom screenshots were visually clean.
  Evidence is in ignored `output/playwright/fe08-*`.
- Decisions: The visually hidden native file input is accessible through its
  semantic large label/drop target and is not a target-size defect.
- Blockers/risks: Independent source/contract/test review is still active.
- Handoff: Move FE-08 to `DONE` and unblock QA-04 only after the reviewer returns
  CLEAN/APPROVE.

### 2026-07-16 12:37 EDT — FE-08 independent review fixes — Codex / ledger_consolidation

- Status: `NEEDS REVIEW`
- Scope: Native File release, narrow-layout containment, focused regressions,
  refreshed distribution/Graphify output, and independent re-review.
- Work: Reset the native file input as well as React state after Remove, invalid
  selection, and profile change, which releases the DOM-held File and permits
  selecting the same file again. Added `min-width`/width containment to the
  account field and wrapping for maximum-length preview filenames and account
  suggestions so valid backend values cannot force narrow-page overflow.
- Verification: Focused import/client **20/20** and full frontend **10 files /
  36 tests** passed. New DOM regressions prove `input.files` clears after Remove
  and profile switch and the same File can be reselected. `npm run build` passed
  (**116 modules**) and refreshed `dist` to `index-DGPe-2ZY.css` and
  `index-Bmm5CWk_.js`; scoped diff check remained clean except line-ending
  warnings. Graphify refreshed to **1,869 nodes / 3,530 edges / 186
  communities**. Independent re-review: **CLEAN/APPROVE** with no remaining
  source, wire-contract, automated-test, or UI source findings.
- Decisions: Both React state and the browser-owned native input value form the
  transient-file privacy boundary and must be cleared together.
- Blockers/risks: Root is running one narrow rendered follow-up on the rebuilt
  distribution using maximum-length unbroken account/filename values at 375px
  and 200% zoom. All previously required rendered gates passed before these
  containment-only fixes.
- Handoff: If the long-value rendered check reports no page overflow, mark FE-08
  `DONE` and unblock QA-04.

### 2026-07-16 12:39 EDT — FE-08 final rendered recheck — Codex / root

- Status: `DONE`
- Scope: Post-review narrow-layout containment acceptance on the final rebuilt
  distribution and task closure.
- Work: Rendered the final Import preview with a 100-character unbroken account
  display name and a 255-character unbroken filename/suggestion matching valid
  backend maximums.
- Verification: At 375px the page measured **375/375** scroll/client width; at
  200% CSS zoom it measured **1440/1440**. Neither case had page-level horizontal
  overflow, and visual inspection confirmed wrapping stayed inside cards and the
  suggestion surface. Evidence is in ignored `output/playwright/fe08-long-*`.
  Together with the earlier full rendered matrix, automated **36/36**, refreshed
  dist, and independent **CLEAN/APPROVE**, every FE-08 acceptance gate passes.
- Decisions: FE-08 is complete; QA-04 is now `READY`.
- Blockers/risks: none. This final workboard-only entry is newer than the
  semantic Graphify documentation pass; AST-derived code relationships are
  current at **1,869 nodes / 3,530 edges / 186 communities**.
- Handoff: Claim QA-04 and execute its cross-app Stage 3 validation matrix.

### 2026-07-16 16:20 EDT — QA-04 — Codex / be11_contract_audit

- Status: `IN PROGRESS`
- Scope: Cross-app Stage 3 validation only; disposable migration/database/temp
  artifacts, loopback runtime and browser evidence, and this workboard. Feature
  source will remain unchanged unless validation proves a defect.
- Work: Claimed the complete import-framework/TD vertical-slice release gate:
  fresh migration cycle, full backend/frontend gates, adversarial lifecycle and
  privacy matrix, loopback binding, and complete Import-button browser flow.
- Verification: pending. `ui-ux-pro-max` was reread in full; its optional
  `scripts/search.py` design-system helper is absent, so the accepted Meridian
  system and the skill's embedded keyboard/focus, target-size, responsive,
  theme, zoom, reduced-motion, form-feedback, and accessibility checks govern
  rendered QA.
- Decisions: Use only committed synthetic TD fixtures. No private statement is
  in scope, and no real statement data will be opened or persisted.
- Blockers/risks: none.
- Handoff: Run the complete QA-04 matrix and record exact pass/fail evidence.

### 2026-07-16 — OPS-CLEAN-01 — Codex / root

- Status: `DONE`
- Scope: Generated test/cache directories under `apps/api`, repository ignore
  rules, and this workboard only. API source, tests, migrations, local data, and
  `.venv` were explicitly preserved.
- Work: Removed 40 disposable pytest scratch roots plus 13 nested Python
  bytecode-cache directories. The deleted tracked scratch roots contained 728
  generated database, fingerprint-key, and test-run files; none were product
  source. Added repository-scoped ignore rules for API `.test-tmp*`, FE test
  scratch, `output`, `beNN-*`, `qaNN-*`, and `pytest-cache-files-*` roots.
- Verification: All deletion targets were resolved and confirmed beneath the
  absolute `apps/api` path before recursive removal. Zero matching generated
  directories remain. The surviving tracked API tree contains 94 intentional
  project files across `app`, `tests`, `alembic`, root configuration, and data;
  ignore probes matched every new pattern. `git diff --check` passed with only
  existing LF/CRLF conversion warnings.
- Decisions: Keep `.venv` ignored and on disk because it is the local Python
  runtime, and preserve `apps/api/data` because it may contain user-local state.
- Blockers/risks: none.
- Handoff: Future backend tests must use ignored scratch roots matching the new
  patterns and must not add generated databases or fingerprint keys to Git.

### 2026-07-17 — BE-BUDGET-01 / FE-BUDGET-01 — Claude Opus 4.8

- Status: `DONE`
- Scope (backend): `apps/api/app/models/budget.py`, `models/{__init__,profile}.py`,
  `schemas/budget.py`, `schemas/__init__.py`, `services/budgets.py`,
  `services/{__init__,errors}.py`, `routers/budgets.py`, `app/main.py`,
  `alembic/versions/0007_budget_models.py`, `tests/test_budget_api.py`, and the
  two pre-existing tests that assert the full table set / no-hard-delete surface.
  Scope (frontend): `apps/web/src/features/budgets/**` (types, api, budgetMath,
  BudgetsPage, budgets.css), `app/AppShell.tsx` (Budgets nav/route/icon),
  `app/pages.tsx` (dashboard Budgets card) and `app/dashboard.css`, refreshed
  `apps/web/dist/`.
- Work: Implemented monthly budgets end-to-end (product plan §11). A `Budget` is
  profile-scoped with a nullable `category_id` (NULL = the single overall budget)
  and a `YYYY-MM` `period_month`; money is a positive integer-cent `limit_cents`.
  Two partial unique indexes enforce one overall budget per profile/month and one
  category budget per profile/category/month; a duplicate returns a new 409
  `ResourceConflictError`. The service validates that a category budget's category
  belongs to the profile (uniform 404 otherwise) and keeps cross-profile reads
  not-found. The Budgets page sets/updates/removes limits, has a month selector,
  and shows progress bars with 75/90/100% threshold states computed from live
  transactions (signed-cents convention, `included_in_spending` only). The
  dashboard's former "Coming soon" Category-budgets card now shows real progress
  bars (worst-utilised first) with a Manage link. Recurring stays "Coming soon"
  (not built).
- Verification: Backend — migration up/down/up from 0006 clean; `test_budget_api`
  13/13; full backend suite **209 passed**; `ruff check app tests alembic` clean.
  Frontend — `npm run typecheck` clean, `npm run test` **36/36**, `npm run build`
  ok and `dist` refreshed. Rendered end-to-end against a live loopback backend
  serving the built dist (fresh migrated DB, seeded profile + budgets in varied
  states): Budgets page and dashboard card verified in light and dark at 1440px
  and at 390px (no horizontal overflow); progress colours match ok/warn/high/over.
- Decisions: Budgets are forward-looking targets, so DELETE is a hard delete
  (unlike profiles/accounts/categories); the no-hard-delete OpenAPI test now
  excludes `/budgets` alongside the existing `/transactions` exclusion. Progress
  is computed client-side from already-loaded transactions rather than a new
  server aggregate, matching the dashboard's existing approach.
- ui-ux checks (skill/graphify unavailable — see FE-01 exception): labelled money
  inputs, real `<button>`s, `role="progressbar"` with aria-value/label, colour
  always paired with a text level ("On track"/"Over budget"), visible focus,
  light+dark via tokens, `prefers-reduced-motion` on bar transitions, and a
  fluid wrap-based responsive row.
- Blockers/risks: none. Recurring-charge detection and the "expected income /
  confirmed recurring" terms of the available-to-save formula (§11.2) remain
  future work; the dashboard hero available-to-save is currently income − spend.
- Handoff: A future slice can add recurring detection (turning the last "Coming
  soon" card real) and fold expected-income/recurring into available-to-save.

### 2026-07-17 — BE-AMEX-01 — Claude Opus 4.8

- Status: `DONE`
- Scope: `apps/api/app/parsers/amex.py` (new), `apps/api/app/parsers/resolver.py`
  (new), `apps/api/app/parsers/__init__.py` (exports), `apps/api/app/routers/imports.py`
  (resolver swap + issuer-neutral docstring), `fixtures/statements/amex/**`
  (generator, three synthetic PDFs, expected canonical JSON, manifest),
  `apps/api/tests/test_amex_parser.py` (new), `apps/api/tests/test_parser_resolver.py`
  (new). The TD parser and import persistence/services were left untouched.
- Work: Implemented the section-aware American Express credit-card parser
  (backlog item 1, first half). Amex groups rows under "Payments and Credits"
  and "New Charges" headings with a single transaction date per row, so the
  parser tracks the active section and derives sign from it (credits = inflow,
  charges = outflow; an explicit negative inside charges is a refund). It
  preserves dates and raw descriptions, stores charged CAD as integer cents,
  classifies payments/refunds/fees/interest, merges multi-line and
  foreign-currency continuations (Decimal exchange rate), and reconciles net +
  debit/credit sections within a one-cent tolerance. Added a `resolve_parser`
  registry that runs each parser's deterministic `detect` and returns the
  highest-confidence match; the preview route now auto-selects the issuer
  instead of hardcoding TD. Unknown issuers raise a readable unsupported error;
  no-text documents raise the scanned-document error.
- Verification: `test_amex_parser` + `test_parser_resolver` **15/15**; full
  backend suite **224 passed** (was 209); `ruff check app tests` clean.
  End-to-end against a live loopback backend: previewed the synthetic Amex PDF
  through `POST /profiles/{id}/imports/preview` — resolver selected
  `amex_credit_card`, 8 rows staged with correct types/signs/foreign-currency/
  occurrence indices, reconciliation delta 0, `validated`; committed it into the
  ledger (8 transactions); a TD statement still routed to `td_credit_card` with
  delta 0 (no regression). Fixture privacy assertions pass (no 12–19 digit runs,
  masked `XXXX-XXXXXX-X1007`, `SYNTHETIC` corpus, no address tokens).
- Decisions: Kept small parse/date helpers local to `amex.py` rather than
  sharing them out of `td.py`, preserving the plan's per-parser file ownership.
  The resolver's registration order is the deterministic tie-breaker for equal
  confidence. Amex rows carry no posting date, so `posted_date` is `None`.
- Exception: This was a direct product-owner request ("work on the import
  feature for Amex statements") made ahead of the QA-04 gate that the backlog
  notes normally require; recorded here as an exception, consistent with prior
  direct-request tasks (GOV-01/02, GRAPH-01). Scope was kept additive and
  disjoint from QA-04's validation surface.
- Blockers/risks: none for the parser. Multi-file import and mixed-issuer
  *batching* (the rest of backlog item 1) remain future work, as does a
  frontend affordance surfacing which issuer parser handled a preview.
- Handoff: A follow-up can add multi-file/mixed-issuer preview batching and,
  separately, the CIBC parser once representative synthetic samples exist.

### 2026-07-17 — BE-RECUR-01 / FE-RECUR-01 — Claude Opus 4.8

- Status: `DONE`
- Scope (backend): `apps/api/app/services/recurring_rules.py` (new pure
  detection), `models/recurring_series.py` (+ Profile relationship + exports),
  `schemas/recurring.py` (+ exports), `services/recurring.py` (+ exports),
  `routers/recurring.py`, `app/main.py`, `alembic/versions/0008_recurring_series.py`,
  `tests/test_recurring_rules.py`, `tests/test_recurring_api.py`, and the two
  pre-existing tests asserting the full table set / no-hard-delete surface.
  Scope (frontend): `apps/web/src/features/recurring/**` (types, api,
  RecurringPage, recurring.css), `app/AppShell.tsx` (nav/route/icon),
  `app/pages.tsx` (dashboard metric + upcoming-recurring card),
  `app/dashboard.css`, refreshed `apps/web/dist/`.
- Work: Implemented recurring-charge / subscription detection end-to-end
  (product plan §12). Detection is a pure, unit-tested heuristic: it groups a
  profile's included debit purchases by a normalized merchant key, recognises
  weekly/biweekly/monthly/quarterly/annual cadence within interval tolerances,
  requires every gap to be within half a period (so irregular frequent
  merchants like groceries/dining are excluded), and grades confidence
  (≥3 consistent + stable amounts = high; ≥3 = medium; 2 = low). Variable
  amounts (utilities) are still detected and reported as a range. `RecurringSeries`
  is profile-scoped with cadence, expected amount + range, next-expected date,
  confidence, rationale, status (keep/review/cancel/ended/ignored per §12.3),
  confirmed flag, and reminder lead days. `POST .../recurring/detect` syncs
  idempotently, preserves user decisions on re-run, and re-links matched
  transactions via the existing `transactions.recurring_series_id`. The Recurring
  page runs detection and shows each series with monthly + annualized cost,
  next-due countdown, confidence badge, rationale, and a keep/review/cancel/
  ignore + confirm workflow; the dashboard's former "Coming soon" upcoming-
  recurring card and metric are now real (est. monthly total + next charges).
- Verification: Backend — migration up/down/up from 0007 clean; recurring rules
  + API **16/16**; full backend suite **240 passed** (was 224); Ruff clean.
  Frontend — `npm run typecheck` clean, `npm run test` **36/36**, `npm run build`
  ok and `dist` refreshed. End-to-end against a live loopback backend: seeded
  Netflix/Spotify (monthly, high), Hydro (monthly, varying → medium range), a
  biweekly gym, plus irregular grocery noise; detection found the four
  subscriptions and correctly ignored the groceries. Recurring page and
  dashboard verified in light and dark at 1440px; the last dashboard "Coming
  soon" placeholder is gone.
- Decisions: Detection considers only `included_in_spending` debit purchases
  (payments/fees/refunds/transfers are not subscriptions). On each detect run
  all profile transaction links are cleared and re-established so links match
  the current ledger. Re-detection never overrides a user status once
  `confirmed_by_user` or a terminal state (cancel/ended/ignored). Recurring
  DELETE is a hard delete (targets, not ledger rows), so the no-hard-delete
  OpenAPI test now also excludes `/recurring`.
- ui-ux checks (skill/graphify unavailable — see FE-01 exception): real
  `<button>` toggles with `aria-pressed`, confidence always paired with a text
  label, ≥34px status targets, visible focus, light/dark via tokens, and a
  wrap-based responsive card.
- Exception: Direct product-owner request ("take on next features") ahead of the
  QA-04 gate; recorded as an exception like BE-AMEX-01. Scope is additive and
  disjoint from QA-04's validation surface.
- Blockers/risks: none. In-app reminders, missing-charge detection, and folding
  confirmed recurring into the §11.2 available-to-save formula remain future
  work (§12.4).
- Handoff: A follow-up can wire confirmed recurring + expected income into
  available-to-save and add reminder surfacing before expected charges.
