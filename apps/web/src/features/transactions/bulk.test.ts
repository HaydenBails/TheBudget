import { describe, expect, it } from 'vitest';
import { buildBulkAction, canBulkInclude } from './bulk';
import type { Transaction } from './types';

function transaction(type: Transaction['type']): Transaction {
  return { id: 1, profile_id: 1, account_id: 1, category_id: null, date: '2026-01-01', posted_date: null, raw_description: 'Test', merchant: '', amount_cents: 100, currency: 'CAD', direction: 'debit', type, categorization_status: 'uncategorized', included_in_spending: false, exclusion_reason: null, recurring_series_id: null, notes: null, source: 'manual', import_id: null, deleted_at: null, created_at: '', updated_at: '' };
}

describe('transaction bulk policy', () => {
  it('allows inclusion only for purchases and cash advances', () => {
    expect(canBulkInclude([transaction('purchase'), transaction('cash_advance')])).toBe(true);
    expect(canBulkInclude([transaction('purchase'), transaction('refund')])).toBe(false);
  });

  it('builds the discriminated BE-11 payloads', () => {
    expect(buildBulkAction('categorize', [1, 2], '', '')).toEqual({ action: 'categorize', transaction_ids: [1, 2], category_id: null });
    expect(buildBulkAction('exclude', [1], '', '  duplicate  ')).toEqual({ action: 'set_spending_inclusion', transaction_ids: [1], included_in_spending: false, exclusion_reason: 'duplicate' });
  });
});
