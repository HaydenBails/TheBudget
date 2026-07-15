import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { Profile, ProfileCreate, ProfileUpdate } from './types';

const KEY = ['profiles'] as const;

export function useProfiles(includeArchived = false) {
  return useQuery({
    queryKey: [...KEY, { includeArchived }],
    queryFn: () => api.get<Profile[]>(`/profiles?include_archived=${includeArchived}`),
  });
}

export function useCreateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileCreate) => api.post<Profile>('/profiles', { base_currency: 'CAD', ...body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ProfileUpdate }) =>
      api.patch<Profile>(`/profiles/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useArchiveProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Profile>(`/profiles/${id}/archive`),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRestoreProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Profile>(`/profiles/${id}/restore`),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
