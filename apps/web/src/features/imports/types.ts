export type ImportStatus = 'staged' | 'ready' | 'committed' | 'cancelled' | 'failed';
export type ValidationStatus = 'validated' | 'validated_with_warnings' | 'needs_review' | 'failed';
export type ImportDuplicateDecision = 'new' | 'blocked_file_hash' | 'blocked_logical_key' | 'potential_overlap';
export type TransactionType = 'purchase' | 'refund' | 'payment' | 'transfer' | 'cash_advance' | 'fee' | 'interest' | 'income' | 'adjustment' | 'unknown';

export interface ImportCandidate {
  id: number;
  source_row_reference: string;
  date: string;
  posted_date: string | null;
  raw_description: string;
  merchant: string;
  amount_cents: number;
  currency: 'CAD';
  direction: 'debit' | 'credit';
  type: TransactionType;
  included_in_spending: boolean;
  exclusion_reason: string | null;
  original_foreign_amount_cents: number | null;
  original_foreign_currency: string | null;
  exchange_rate: string | null;
  occurrence_index: number;
  duplicate_decision: 'new' | 'skip_exact' | 'potential_overlap' | 'keep';
  status: 'pending' | 'accepted' | 'skipped' | 'needs_review';
}

export interface ImportWarning {
  id: number;
  code: string;
  severity: 'info' | 'warning' | 'error';
  message: string;
  source_row_reference: string | null;
}

export interface ImportDetail {
  id: number;
  profile_id: number;
  account_id: number;
  issuer: string;
  source_filename: string;
  parser_name: string;
  parser_version: string;
  statement_start_date: string | null;
  statement_end_date: string | null;
  currency: 'CAD';
  status: ImportStatus;
  validation_status: ValidationStatus;
  duplicate_decision: ImportDuplicateDecision;
  duplicate_of_import_id: number | null;
  transaction_count: number;
  purchase_count: number;
  credit_count: number;
  payment_count: number;
  fee_interest_count: number;
  unresolved_count: number;
  expected_total_cents: number | null;
  parsed_total_cents: number | null;
  reconciliation_delta_cents: number | null;
  purchase_total_cents: number | null;
  credit_total_cents: number | null;
  payment_total_cents: number | null;
  fee_interest_total_cents: number | null;
  staged_transactions: ImportCandidate[];
  warnings: ImportWarning[];
}

export interface ImportPreview extends ImportDetail {
  suggested_account_id: number | null;
}

export interface ImportCommitResult {
  import_id: number;
  status: 'committed';
  created_count: number;
  linked_duplicate_count: number;
  transaction_ids: number[];
}
