export type TransactionType =
  | 'purchase'
  | 'refund'
  | 'payment'
  | 'transfer'
  | 'cash_advance'
  | 'fee'
  | 'interest'
  | 'income'
  | 'adjustment'
  | 'unknown';

export type Direction = 'debit' | 'credit';
export type CategorizationStatus = 'suggested' | 'confirmed' | 'rule_applied' | 'manual' | 'uncategorized';
export type TransactionSource = 'pdf_import' | 'csv_import' | 'manual';

export interface Transaction {
  id: number;
  profile_id: number;
  account_id: number;
  category_id: number | null;
  date: string;
  posted_date: string | null;
  raw_description: string;
  merchant: string;
  amount_cents: number;
  currency: 'CAD';
  direction: Direction;
  type: TransactionType;
  categorization_status: CategorizationStatus;
  included_in_spending: boolean;
  exclusion_reason: string | null;
  recurring_series_id: number | null;
  notes: string | null;
  source: TransactionSource;
  import_id: number | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionSplit {
  id: number;
  transaction_id: number;
  category_id: number;
  amount_cents: number;
  created_at: string;
  updated_at: string;
}

export interface TransactionTag {
  id: number;
  profile_id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionDetail extends Transaction {
  splits: TransactionSplit[];
  tags: TransactionTag[];
}

export interface TransactionCreate {
  account_id: number;
  date: string;
  posted_date?: string | null;
  raw_description: string;
  merchant?: string;
  amount_cents: number;
  currency?: 'CAD';
  direction: Direction;
  type?: TransactionType;
  category_id?: number | null;
  notes?: string | null;
  source?: TransactionSource;
}

export interface TransactionUpdate {
  date?: string;
  posted_date?: string | null;
  raw_description?: string;
  merchant?: string;
  amount_cents?: number;
  direction?: Direction;
  type?: TransactionType;
  category_id?: number | null;
  categorization_status?: CategorizationStatus;
  included_in_spending?: boolean;
  exclusion_reason?: string | null;
  notes?: string | null;
}

export interface TransactionFilters {
  accountId: number | null;
  categoryId: number | null;
  type: TransactionType | null;
  dateFrom: string;
  dateTo: string;
  includedInSpending: boolean | null;
  search: string;
  includeDeleted: boolean;
}

export type TransactionBulkAction =
  | { action: 'categorize'; transaction_ids: number[]; category_id: number | null }
  | {
      action: 'set_spending_inclusion';
      transaction_ids: number[];
      included_in_spending: boolean;
      exclusion_reason?: string;
    };

export interface TransactionBulkResult {
  updated_count: number;
  transactions: Transaction[];
}

export interface TransactionDeletedResult {
  id: number;
  deleted: boolean;
}

export const TRANSACTION_TYPES: ReadonlyArray<{ value: TransactionType; label: string }> = [
  { value: 'purchase', label: 'Purchase' },
  { value: 'refund', label: 'Refund' },
  { value: 'payment', label: 'Payment' },
  { value: 'transfer', label: 'Transfer' },
  { value: 'cash_advance', label: 'Cash advance' },
  { value: 'fee', label: 'Fee' },
  { value: 'interest', label: 'Interest' },
  { value: 'income', label: 'Income' },
  { value: 'adjustment', label: 'Adjustment' },
  { value: 'unknown', label: 'Unknown' },
];

export function transactionTypeLabel(value: TransactionType): string {
  return TRANSACTION_TYPES.find((item) => item.value === value)?.label ?? value;
}
