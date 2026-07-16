import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type {
  Transaction,
  TransactionBulkAction,
  TransactionBulkResult,
  TransactionCreate,
  TransactionDeletedResult,
  TransactionDetail,
  TransactionFilters,
  TransactionSplit,
  TransactionTag,
  TransactionUpdate,
} from './types';

export const transactionKey = (profileId: number) => ['transactions', profileId] as const;
const base = (profileId: number) => `/profiles/${profileId}/transactions`;

export function transactionListPath(profileId: number, filters: TransactionFilters): string {
  const params = new URLSearchParams();
  if (filters.accountId != null) params.set('account_id', String(filters.accountId));
  if (filters.categoryId != null) params.set('category_id', String(filters.categoryId));
  if (filters.type) params.set('type', filters.type);
  if (filters.dateFrom) params.set('date_from', filters.dateFrom);
  if (filters.dateTo) params.set('date_to', filters.dateTo);
  if (filters.includedInSpending != null) params.set('included_in_spending', String(filters.includedInSpending));
  if (filters.search.trim()) params.set('search', filters.search.trim());
  if (filters.includeDeleted) params.set('include_deleted', 'true');
  const query = params.toString();
  return `${base(profileId)}${query ? `?${query}` : ''}`;
}

export function useTransactions(profileId: number | null, filters: TransactionFilters) {
  return useQuery({
    queryKey: [...(profileId ? transactionKey(profileId) : ['transactions', 'none']), filters],
    queryFn: () => api.get<Transaction[]>(transactionListPath(profileId as number, filters)),
    enabled: profileId != null,
  });
}

export function useTransactionDetail(profileId: number | null, transactionId: number | null) {
  return useQuery({
    queryKey: [...(profileId ? transactionKey(profileId) : ['transactions', 'none']), 'detail', transactionId],
    queryFn: () => api.get<TransactionDetail>(`${base(profileId as number)}/${transactionId}`),
    enabled: profileId != null && transactionId != null,
  });
}

function invalidator(profileId: number, qc: ReturnType<typeof useQueryClient>) {
  return () => qc.invalidateQueries({ queryKey: transactionKey(profileId) });
}

export function useCreateTransaction(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TransactionCreate) => api.post<Transaction>(base(profileId), body),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useUpdateTransaction(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: TransactionUpdate }) => api.patch<Transaction>(`${base(profileId)}/${id}`, body),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useReplaceTransactionSplits(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, splits }: { id: number; splits: Array<{ category_id: number; amount_cents: number }> }) =>
      api.put<TransactionSplit[]>(`${base(profileId)}/${id}/splits`, { splits }),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useReplaceTransactionTags(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, tags }: { id: number; tags: string[] }) =>
      api.put<TransactionTag[]>(`${base(profileId)}/${id}/tags`, { tags: tags.map((name) => ({ name })) }),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useBulkUpdateTransactions(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TransactionBulkAction) => api.patch<TransactionBulkResult>(`${base(profileId)}/bulk`, body),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useDeleteTransaction(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<TransactionDeletedResult>(`${base(profileId)}/${id}`),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useRestoreTransaction(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<TransactionDeletedResult>(`${base(profileId)}/${id}/restore`),
    onSuccess: invalidator(profileId, qc),
  });
}
