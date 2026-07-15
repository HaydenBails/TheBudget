import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { Account, AccountCreate, AccountUpdate } from './types';

const key = (profileId: number) => ['accounts', profileId] as const;
const base = (profileId: number) => `/profiles/${profileId}/accounts`;

export function useAccounts(profileId: number | null, includeArchived = false) {
  return useQuery({
    queryKey: [...(profileId ? key(profileId) : ['accounts', 'none']), { includeArchived }],
    queryFn: () => api.get<Account[]>(`${base(profileId as number)}?include_archived=${includeArchived}`),
    enabled: profileId != null,
  });
}

export function useCreateAccount(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AccountCreate) => api.post<Account>(base(profileId), { currency: 'CAD', ...body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}

export function useUpdateAccount(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: AccountUpdate }) =>
      api.patch<Account>(`${base(profileId)}/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}

export function useArchiveAccount(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Account>(`${base(profileId)}/${id}/archive`),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}

export function useRestoreAccount(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Account>(`${base(profileId)}/${id}/restore`),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}
