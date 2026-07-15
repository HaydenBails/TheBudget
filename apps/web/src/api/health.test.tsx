import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as client from './client';
import { useHealth } from './health';

function Probe() {
  const { isLoading, isError, data } = useHealth();
  if (isLoading) return <span>loading</span>;
  if (isError) return <span>error</span>;
  return <span>ok:{data?.service}</span>;
}

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('useHealth request states', () => {
  it('shows loading, then the connected/success state', async () => {
    vi.spyOn(client.api, 'get').mockResolvedValue({ status: 'ok', service: 'spending-tracker-api', version: 'x' });
    renderWithClient(<Probe />);
    expect(screen.getByText('loading')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('ok:spending-tracker-api')).toBeInTheDocument());
  });

  it('shows the error/offline state when the request fails', async () => {
    vi.spyOn(client.api, 'get').mockRejectedValue(new client.ApiError('offline', 0));
    renderWithClient(<Probe />);
    await waitFor(() => expect(screen.getByText('error')).toBeInTheDocument());
  });
});
