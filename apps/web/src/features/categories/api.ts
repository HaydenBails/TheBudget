import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import type { Category, CategoryCreate, CategoryUpdate } from './types';

const key = (profileId: number) => ['categories', profileId] as const;
const base = (profileId: number) => `/profiles/${profileId}/categories`;

export function useCategories(profileId: number | null, includeArchived = false) {
  return useQuery({
    queryKey: [...(profileId ? key(profileId) : ['categories', 'none']), { includeArchived }],
    queryFn: () => api.get<Category[]>(`${base(profileId as number)}?include_archived=${includeArchived}`),
    enabled: profileId != null,
  });
}

export function useCreateCategory(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CategoryCreate) => api.post<Category>(base(profileId), body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}

export function useUpdateCategory(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CategoryUpdate }) =>
      api.patch<Category>(`${base(profileId)}/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}

export function useArchiveCategory(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Category>(`${base(profileId)}/${id}/archive`),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}

export function useRestoreCategory(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Category>(`${base(profileId)}/${id}/restore`),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(profileId) }),
  });
}
