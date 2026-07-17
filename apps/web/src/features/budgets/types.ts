// Budget wire types — mirror apps/api/app/schemas/budget.py exactly.

export interface Budget {
  id: number;
  profile_id: number;
  /** null = the profile's overall monthly budget; otherwise a category budget. */
  category_id: number | null;
  /** Calendar month the budget applies to, e.g. "2026-07". */
  period_month: string;
  limit_cents: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetCreate {
  category_id?: number | null;
  period_month: string;
  limit_cents: number;
}

export interface BudgetUpdate {
  limit_cents?: number;
}
