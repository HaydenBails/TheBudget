// Shared domain types for the Stage 1 UI prototypes.
// These mirror (a simplified slice of) the canonical model in the product plan.
// All money is stored as integer CENTS (never floating point). Base currency CAD.

export type IssuerCode = 'TD' | 'AMEX' | 'CIBC' | 'OTHER';

export type TransactionType =
  | 'purchase'
  | 'refund'
  | 'payment' // credit-card payment / transfer, excluded from spending
  | 'cash_advance'
  | 'fee'
  | 'interest'
  | 'income'
  | 'adjustment'
  | 'unknown';

export type CategorizationStatus =
  | 'suggested'
  | 'confirmed'
  | 'rule-applied'
  | 'manual'
  | 'uncategorized';

export interface Category {
  id: string;
  name: string;
  /** Hex colour, used consistently across every chart and badge. */
  color: string;
  /** Emoji/icon token — never rely on colour alone (a11y). */
  icon: string;
  /** Categories flagged excluded never count toward core spending. */
  excludedFromSpending?: boolean;
}

export interface Account {
  id: string;
  issuer: IssuerCode;
  /** User-defined display name. */
  name: string;
  color: string;
  /** Masked digits only — never a full card number. */
  last4: string;
  currency: string; // ISO code, 'CAD'
  archived?: boolean;
}

export interface Transaction {
  id: string;
  accountId: string;
  /** ISO date (YYYY-MM-DD) the purchase occurred. */
  date: string;
  /** ISO date it posted, nullable. */
  postedDate?: string;
  /** Untouched original statement description. */
  rawDescription: string;
  /** Cleaned, human-friendly merchant name. */
  merchant: string;
  /** Signed amount in integer cents. Purchases negative, refunds/income positive. */
  amountCents: number;
  currency: string;
  type: TransactionType;
  /** null until reviewed. */
  categoryId: string | null;
  categorizationStatus: CategorizationStatus;
  /** 0..1 confidence for a suggestion. */
  confidence?: number;
  /** Human-readable reason the suggestion was made. */
  reason?: string;
  /** Whether this row counts toward core spending totals. */
  includedInSpending: boolean;
  /** If excluded, why (shown in UI). */
  exclusionReason?: string;
  recurringSeriesId?: string | null;
  notes?: string;
  tags?: string[];
}

export type RecurringStatus = 'keep' | 'review' | 'cancel' | 'ended' | 'ignored';
export type RecurringCadence = 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annual';

export interface RecurringSeries {
  id: string;
  accountId: string | null;
  name: string;
  merchant: string;
  categoryId: string | null;
  /** Expected amount in cents (magnitude). */
  expectedAmountCents: number;
  cadence: RecurringCadence;
  nextExpectedDate: string;
  confidence: number;
  status: RecurringStatus;
  reason: string;
}

export type IncomeFrequency = 'weekly' | 'biweekly' | 'monthly';

export interface IncomeSchedule {
  id: string;
  name: string;
  amountCents: number;
  frequency: IncomeFrequency;
  nextDate: string;
  active: boolean;
}

export interface Budget {
  /** null categoryId => overall monthly budget. */
  categoryId: string | null;
  monthlyLimitCents: number;
}
