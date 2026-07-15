# End-to-end tests

**Playwright** end-to-end tests will live here in a later stage. They drive the
web UI against a running local API and a seeded local SQLite database to verify
complete user journeys. Nothing runs yet — this is a stub.

## Key scenarios (product plan §22.4)

1. **Create profile** — create a new isolated profile and land on its empty state.
2. **Import TD statement** — import a synthetic TD statement; transactions appear
   normalized (amounts in integer cents), with correct `txn_type` classification.
3. **Re-import dedup** — re-importing the same statement produces **no duplicate**
   transactions (dedupe by hash).
4. **Categorize** — assign/change a category on a transaction; a rule can be
   learned from the correction.
5. **Split / tag / delete / restore** — split a transaction across categories,
   add tags, soft-delete, then restore it.
6. **Income + budgets** — record income and set category budgets; budget
   consumption reflects only included spending.
7. **Recurring forecast** — detect a recurring charge and show its forecast.
8. **Export** — export transactions/summary and verify contents.
9. **Profile isolation** — data created in one profile is **not visible** in
   another; deleting a profile removes only its data.

## Prerequisites (future)

- Node 20+, Playwright browsers installed.
- A local API instance and a seeded synthetic dataset (never real statements).
