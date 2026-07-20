import type { Transaction, TransactionBulkAction } from './types';

export type BulkActionChoice = 'categorize' | 'include' | 'exclude';

export function canBulkInclude(transactions: Transaction[]): boolean {
  return transactions.length > 0 && transactions.every((transaction) => transaction.type === 'purchase' || transaction.type === 'cash_advance' || transaction.type === 'refund');
}

export function buildBulkAction(choice: BulkActionChoice, transactionIds: number[], categoryId: string, reason: string): TransactionBulkAction {
  if (choice === 'categorize') {
    return { action: 'categorize', transaction_ids: transactionIds, category_id: categoryId ? Number(categoryId) : null };
  }
  return {
    action: 'set_spending_inclusion',
    transaction_ids: transactionIds,
    included_in_spending: choice === 'include',
    ...(choice === 'exclude' ? { exclusion_reason: reason.trim() } : {}),
  };
}
