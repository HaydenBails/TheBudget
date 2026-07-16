# 2. Stage-1 UI directions

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

Before committing to production UI components, we evaluated distinct visual and
interaction approaches against the same screens and synthetic dataset. The
product is desktop-first and data-dense, so the chosen direction must support
transaction grids, category review, and spending charts in light and dark mode.

## Decision history

Stage 1 compared three directions:

- **Aurora** — calm, modern banking feel; indigo palette; generous spacing.
- **Ledger** — dense, data-forward; sky-blue palette; compact rows.
- **Horizon** — bold and colourful; orange palette; chart-led.

Meridian was initially selected on 2026-07-15. On 2026-07-16 the product owner
briefly superseded that choice with Ledger, then issued a newer direct decision
to retain the live API-backed application while returning its production visual
system to **Meridian**. The newest decision governs.

## Current production direction

**Meridian** is selected: approachable, professional, and data-capable, with
blue-violet accents, rounded surfaces, gentle depth, clear hierarchy, and the
existing top-navigation model. Transaction tables remain precise and compact
enough for real finance work.

Production must retain visible focus, pointer and keyboard operation, at least
44px targets, responsive layouts, light/dark contrast, 200% zoom support, and
reduced-motion behavior.

The comparison harness, synthetic runtime dataset, and all old prototype routes
(including the original Meridian prototype) remain retired. Production screens
use live local API data and one Meridian token system; this decision does not
restore prototype or mock-data code.

## Consequences

- **Positive:** Meridian keeps the production app friendly and coherent without
  sacrificing the real transaction, account, category, and profile workflows.
- **Trade-off:** softer surfaces and larger radii must not reduce table density
  or information contrast; those qualities require explicit QA.
- **Follow-up:** maintain a single Meridian production token system, keep the
  comparison/sample-data runtime removed, and build new screens against live
  local APIs only.
