import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type {
  IncomeOccurrence,
  IncomeSchedule,
  IncomeScheduleCreate,
  IncomeScheduleUpdate,
} from './types';

const key = (profileId: number) => ['income', profileId] as const;
const base = (profileId: number) => `/profiles/${profileId}/income`;

export function useIncomeSchedules(profileId: number | null) {
  return useQuery({
    queryKey: profileId ? key(profileId) : ['income', 'none'],
    queryFn: () => api.get<IncomeSchedule[]>(base(profileId as number)),
    enabled: profileId != null,
  });
}

export function useIncomeOccurrences(profileId: number | null, from: string, to: string) {
  return useQuery({
    queryKey: [...(profileId ? key(profileId) : ['income', 'none']), 'occ', from, to],
    queryFn: () =>
      api.get<IncomeOccurrence[]>(`${base(profileId as number)}/occurrences?date_from=${from}&date_to=${to}`),
    enabled: profileId != null,
  });
}

function invalidate(profileId: number, qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: key(profileId) });
}

export function useCreateIncome(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IncomeScheduleCreate) => api.post<IncomeSchedule>(base(profileId), body),
    onSuccess: () => invalidate(profileId, qc),
  });
}

export function useUpdateIncome(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: IncomeScheduleUpdate }) =>
      api.patch<IncomeSchedule>(`${base(profileId)}/${id}`, body),
    onSuccess: () => invalidate(profileId, qc),
  });
}

export function useDeleteIncome(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`${base(profileId)}/${id}`),
    onSuccess: () => invalidate(profileId, qc),
  });
}
