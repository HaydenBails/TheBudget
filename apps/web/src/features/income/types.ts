// Income wire types — mirror apps/api/app/schemas/income.py exactly.

export type Frequency = 'weekly' | 'biweekly' | 'monthly';

export interface IncomeSchedule {
  id: number;
  profile_id: number;
  name: string;
  amount_cents: number;
  frequency: Frequency;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  notes: string | null;
  next_expected_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncomeScheduleCreate {
  name: string;
  amount_cents: number;
  frequency: Frequency;
  start_date: string;
  end_date?: string | null;
  is_active?: boolean;
  notes?: string | null;
}

export interface IncomeScheduleUpdate {
  name?: string;
  amount_cents?: number;
  frequency?: Frequency;
  start_date?: string;
  end_date?: string | null;
  is_active?: boolean;
  notes?: string | null;
}

export interface IncomeOccurrence {
  schedule_id: number;
  name: string;
  occurrence_date: string;
  amount_cents: number;
}

export const FREQUENCY_LABEL: Record<Frequency, string> = {
  weekly: 'Weekly',
  biweekly: 'Every 2 weeks',
  monthly: 'Monthly',
};

/** Monthly-equivalent cash flow of a schedule, in cents. */
export function monthlyEquivalentCents(s: IncomeSchedule): number {
  const perYear: Record<Frequency, number> = { weekly: 52, biweekly: 26, monthly: 12 };
  return Math.round((s.amount_cents * perYear[s.frequency]) / 12);
}
