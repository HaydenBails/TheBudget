import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as client from '../../api/client';
import { useCreateProfile, useProfiles } from './api';
import type { Profile } from './types';

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const sample: Profile = {
  id: 1,
  name: 'Personal',
  base_currency: 'CAD',
  is_archived: false,
  created_at: '2026-07-15T00:00:00Z',
  updated_at: '2026-07-15T00:00:00Z',
};

describe('profiles hooks', () => {
  it('useProfiles loads the list and requests the active-only scope', async () => {
    const get = vi.spyOn(client.api, 'get').mockResolvedValue([sample]);
    const { result } = renderHook(() => useProfiles(false), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].name).toBe('Personal');
    expect(get).toHaveBeenCalledWith('/profiles?include_archived=false');
  });

  it('useCreateProfile posts a create body defaulting the currency', async () => {
    const post = vi.spyOn(client.api, 'post').mockResolvedValue(sample);
    const { result } = renderHook(() => useCreateProfile(), { wrapper: wrapper() });
    await result.current.mutateAsync({ name: 'Personal' });
    expect(post).toHaveBeenCalledWith('/profiles', { base_currency: 'CAD', name: 'Personal' });
  });
});
