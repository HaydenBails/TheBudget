# Implementation workboard

- **Purpose:** Single source of truth for implementation planning and AI handoffs
- **Current phase:** Stage 1 sign-off → Stage 2 foundation
- **Production UI direction:** Meridian, approved by the product owner
- **Last updated:** 2026-07-15

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
- The existing Aurora, Ledger, and Horizon prototypes are references, not the
  production application.

Read before implementation:

- [`0001-tech-stack.md`](decisions/0001-tech-stack.md)
- [`0002-ui-directions.md`](decisions/0002-ui-directions.md)
- [`0003-money-and-accounting.md`](decisions/0003-money-and-accounting.md)
- [`architecture/overview.md`](architecture/overview.md)

## Milestones

| Milestone | Exit condition | Status |
| --- | --- | --- |
| M0 — Stage 1 closure | Meridian is signed off and ADR 0002 records the final decision. | `DONE` |
| M1 — Development foundation | Database, migrations, app shell, API client, and test foundations work. | `IN PROGRESS` |
| M2 — Profiles and accounts | A user can create/switch profiles and manage isolated accounts. | `BLOCKED` |
| M3 — Core ledger schema | Categories and transactions persist with exact money semantics. | `BLOCKED` |
| M4 — First production workspace | Meridian shell displays API-backed profile/account data reliably. | `BLOCKED` |

## Dependency map

```text
S1-01
  ├── BE-01 ── BE-02 ── BE-03 ── BE-04 ── BE-05
  │                                  └────── BE-06
  └── FE-01 ── FE-02 ── FE-03 ── FE-04 ── FE-05
                                      │         │
                                      └── INT-01 ┘
BE-05 + BE-06 + FE-05 + INT-01 ── QA-01 ── DOC-01
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
| FE-02 | Create production application shell and routes separate from the comparison harness. | FE-01 | `apps/web/src/app/`, `apps/web/src/main.tsx`, reusable components | Production routes render Meridian navigation and theme; prototype routes remain accessible for reference; keyboard navigation works. | `READY` | — |
| FE-03 | Install/configure TanStack Query and define the typed local API client/error model. | FE-02 | `apps/web/package*.json`, `apps/web/src/api/`, query client | Lockfile is consistent; health request works; loading/error states are tested; API base defaults to loopback/local configuration. | `BLOCKED` | — |
| FE-04 | Build profile switcher and profile management UI. | FE-03, BE-05 | `apps/web/src/features/profiles/` | List/create/select/delete flows work against API; destructive action confirms; loading, empty, and error states exist. | `BLOCKED` | — |
| FE-05 | Build account management UI for the active profile. | FE-04, BE-05 | `apps/web/src/features/accounts/` | Account list/create/edit/delete stays scoped to active profile; form validation and empty/error states are covered. | `BLOCKED` | — |

### Integration, quality, and documentation

| ID | Task | Depends on | Primary scope | Acceptance and verification | Status | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| INT-01 | Add isolated integration-test database and frontend API mocking/test harness. | BE-05, FE-03 | API test fixtures, web test configuration | Tests never touch the user's real database; backend API tests and frontend request-state tests run deterministically. | `BLOCKED` | — |
| QA-01 | Validate the complete profiles/accounts vertical slice. | BE-05, BE-06, FE-05, INT-01 | Cross-app review; avoid feature edits unless defects are found | Clean setup, migrations, backend tests/lint, frontend typecheck/build/tests, loopback startup, keyboard smoke test, and profile-isolation scenarios pass. | `BLOCKED` | — |
| DOC-01 | Update setup, architecture, API, and user-flow documentation after the slice lands. | QA-01 | `README.md`, `docs/architecture/`, `apps/api/README.md` | A new developer can reproduce setup and the documented behavior matches verified commands. | `BLOCKED` | — |

## Later-stage backlog

Do not claim these until the profiles/accounts vertical slice is complete and
the board has been expanded with equivalent acceptance detail.

1. Categories, seed categories, and profile-specific overrides.
2. Core transaction, split, tag, import, budget, recurring-series, and rule
   schemas.
3. Production TanStack transaction grid using API-backed data.
4. Temporary upload/staging/preview/commit import framework.
5. TD parser and reconciliation fixtures.
6. Amex and CIBC discovery/parsers.
7. Categorization, merchant normalization, and remembered rules.

## Known blockers and decisions needed

| ID | Item | Owner | Resolution needed |
| --- | --- | --- | --- |
| D-01 | Meridian is selected but ADR 0002 still says final sign-off is pending. | Product owner | `RESOLVED` — Meridian approved as-is on 2026-07-15 and ADR 0002 updated. |
| D-02 | Production prototype retention/removal timing is not explicit. | Product owner/lead agent | Default: keep all prototypes accessible until the first production vertical slice passes QA. |

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
