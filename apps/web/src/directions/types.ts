import type { ComponentType } from 'react';

/** Metadata describing a UI design direction (a Stage 1 prototype). */
export interface DirectionMeta {
  id: string;
  /** Working name, e.g. "Aurora". */
  name: string;
  /** One-line description of the aesthetic. */
  tagline: string;
  /** Short paragraph of what distinguishes this direction. */
  description: string;
  /** Signature accent colour (hex) used on the landing card. */
  accent: string;
}

/**
 * Each design direction implements this contract. The three prototype screens
 * MUST all consume the shared dataset via `src/lib/derived.ts` — a direction
 * never invents its own financial numbers. A direction owns its full page
 * chrome (its own sidebar/topbar/layout); the harness only overlays a small
 * floating switcher for comparison.
 */
export interface Direction {
  meta: DirectionMeta;
  Dashboard: ComponentType;
  Transactions: ComponentType;
  Review: ComponentType;
}

export type ScreenKey = 'dashboard' | 'transactions' | 'review';
