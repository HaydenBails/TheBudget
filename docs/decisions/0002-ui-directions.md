# 2. Stage-1 UI directions

- **Status:** Accepted (pending final sign-off)
- **Date:** 2026-07-15

## Context

Before committing to production UI components, we want to evaluate distinct
visual and interaction approaches against real screens and real (synthetic)
data, rather than debating in the abstract. The product is desktop-first and
data-dense (transaction grids, category review, spending/savings charts), so the
chosen direction must hold up under density, in both light and dark mode.

## Decision

Build **three comparable UI directions** on a single shared **synthetic
dataset**, each implementing the same core screens (Dashboard, Transactions,
Review Categories) so they can be compared apples-to-apples:

- **Aurora** — calm, modern banking feel; **indigo** palette; generous spacing;
  soft depth.
- **Ledger** — dense, data-forward; **sky-blue** palette; compact rows;
  spreadsheet-like clarity.
- **Horizon** — bold and colourful; **orange** palette; high-contrast accents;
  chart-led.

After reviewing the three, the selected direction is a **blend of Ledger and
Horizon**, implemented as a fourth direction:

- **Meridian** *(selected)* — Ledger's information **density** and precise
  tabular numbers, softened with Horizon's **rounded cards, gentle gradients and
  warmth**. Blue-violet (`#4f6bff`) palette. Goal: professional but friendly.
  Soft top-bar nav with a rounded active pill; a gradient hero KPI alongside a
  compact secondary-metric row; dense-but-comfortable tables with monospace
  descriptions; a review flow that pairs Horizon's large friendly category
  buttons with a Ledger-style queue rail.

The three originals (Aurora, Ledger, Horizon) are retained in the repo for
reference/comparison but are **not** the production direction. Final visual
sign-off from the product owner is still pending; Stage 2 builds on Meridian.

### Prototype variables being compared

| Variable          | What we are evaluating                                              |
| ----------------- | ------------------------------------------------------------------- |
| **Palette**       | Indigo (Aurora) vs sky-blue (Ledger) vs orange (Horizon) vs blue-violet (Meridian). |
| **Nav style**     | Sidebar vs top-bar vs hybrid; wayfinding and screen switching.      |
| **Metric density**| How many KPIs/metrics per view; breathing room vs information mass.  |
| **Chart emphasis**| Charts as hero vs charts as support to the tables.                  |
| **Light/dark**    | Legibility, contrast, and accent behaviour in both themes.          |

## Consequences

- **Positive:** the choice is grounded in interactive prototypes on identical
  data; density and dark-mode weaknesses surface early; a clear vocabulary
  (Aurora/Ledger/Horizon) for discussing direction.
- **Negative / trade-offs:** building three directions costs more up front and
  produces throwaway prototype code; production components are deferred until a
  direction is selected.
- **Follow-up:** once selected, extract shared design tokens/components into
  `packages/ui` and retire the unused prototypes.
