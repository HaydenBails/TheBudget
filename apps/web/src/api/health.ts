import { useQuery } from '@tanstack/react-query';
import { api } from './client';

export interface Health {
  status: string;
  service: string;
  version: string;
}

/** Health of the local API. Used to show connection state in the shell. */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<Health>('/health'),
    retry: 0,
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
}
