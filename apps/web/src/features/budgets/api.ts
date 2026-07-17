import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { Budget, BudgetCreate, BudgetUpdate } from './types';

const key = (profileId: number) => ['budgets', profileId] as const;
const base = (profileId: number) => `/profiles/${profileId}/budgets`;

export function useBudgets(profileId: number | null, periodMonth?: string) {
  return useQuery({
    queryKey: [...(profileId ? key(profileId) : ['budgets', 'none']), periodMonth ?? 'all'],
    queryFn: () => {
      const q = periodMonth ? `?period_month=${periodMonth}` : '';
      return api.get<Budget[]>(`${base(profileId as number)}${q}`);
    },
    enabled: profileId != null,
  });
}

function invalidator(profileId: number, qc: ReturnType<typeof useQueryClient>) {
  return () => qc.invalidateQueries({ queryKey: key(profileId) });
}

export function useCreateBudget(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BudgetCreate) => api.post<Budget>(base(profileId), body),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useUpdateBudget(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: BudgetUpdate }) =>
      api.patch<Budget>(`${base(profileId)}/${id}`, body),
    onSuccess: invalidator(profileId, qc),
  });
}

export function useDeleteBudget(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`${base(profileId)}/${id}`),
    onSuccess: invalidator(profileId, qc),
  });
}
