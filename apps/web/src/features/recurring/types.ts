// Recurring-charge wire types — mirror apps/api/app/schemas/recurring.py exactly.

export type Cadence = 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annual';
export type Confidence = 'high' | 'medium' | 'low';
export type RecurringStatus = 'keep' | 'review' | 'cancel' | 'ended' | 'ignored';

export interface RecurringSeries {
  id: number;
  profile_id: number;
  account_id: number | null;
  category_id: number | null;
  merchant_key: string;
  display_name: string;
  amount_cents: number;
  amount_min_cents: number;
  amount_max_cents: number;
  cadence: Cadence;
  interval_days: number;
  confidence: Confidence;
  status: RecurringStatus;
  confirmed_by_user: boolean;
  reminder_lead_days: number;
  occurrence_count: number;
  first_charge_date: string;
  last_charge_date: string;
  next_expected_date: string;
  rationale: string;
  created_at: string;
  updated_at: string;
}

export interface RecurringSeriesUpdate {
  status?: RecurringStatus;
  confirmed_by_user?: boolean;
  reminder_lead_days?: number;
  display_name?: string;
}

export interface RecurringDetectResult {
  detected: number;
  created: number;
  updated: number;
  series: RecurringSeries[];
}

/** Approximate monthly-equivalent cost of a cadence, in cents. */
export function monthlyCostCents(s: RecurringSeries): number {
  const perYear: Record<Cadence, number> = {
    weekly: 52,
    biweekly: 26,
    monthly: 12,
    quarterly: 4,
    annual: 1,
  };
  return Math.round((s.amount_cents * perYear[s.cadence]) / 12);
}

export function annualCostCents(s: RecurringSeries): number {
  const perYear: Record<Cadence, number> = {
    weekly: 52,
    biweekly: 26,
    monthly: 12,
    quarterly: 4,
    annual: 1,
  };
  return s.amount_cents * perYear[s.cadence];
}

export const CADENCE_LABEL: Record<Cadence, string> = {
  weekly: 'Weekly',
  biweekly: 'Every 2 weeks',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  annual: 'Yearly',
};
