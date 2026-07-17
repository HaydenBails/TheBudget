import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { RecurringDetectResult, RecurringSeries, RecurringSeriesUpdate } from './types';

const key = (profileId: number) => ['recurring', profileId] as const;
const base = (profileId: number) => `/profiles/${profileId}/recurring`;

export function useRecurringSeries(profileId: number | null) {
  return useQuery({
    queryKey: profileId ? key(profileId) : ['recurring', 'none'],
    queryFn: () => api.get<RecurringSeries[]>(base(profileId as number)),
    enabled: profileId != null,
  });
}

function invalidate(profileId: number, qc: ReturnType<typeof useQueryClient>) {
  // Detection re-links transactions, so refresh those too.
  qc.invalidateQueries({ queryKey: key(profileId) });
  qc.invalidateQueries({ queryKey: ['transactions', profileId] });
}

export function useDetectRecurring(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<RecurringDetectResult>(`${base(profileId)}/detect`),
    onSuccess: () => invalidate(profileId, qc),
  });
}

export function useUpdateRecurring(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: RecurringSeriesUpdate }) =>
      api.patch<RecurringSeries>(`${base(profileId)}/${id}`, body),
    onSuccess: () => invalidate(profileId, qc),
  });
}

export function useDeleteRecurring(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`${base(profileId)}/${id}`),
    onSuccess: () => invalidate(profileId, qc),
  });
}
