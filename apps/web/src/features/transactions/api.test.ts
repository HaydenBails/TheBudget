import { createElement, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import * as client from '../../api/client';
import { transactionListPath, useTransactions } from './api';
import type { TransactionFilters } from './types';

const emptyFilters: TransactionFilters = { accountId: null, categoryId: null, type: null, dateFrom: '', dateTo: '', includedInSpending: null, search: '', includeDeleted: false };

function wrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => createElement(QueryClientProvider, { client: queryClient }, children);
}

describe('transaction API paths', () => {
  it('serializes only active filters under the profile-scoped route', () => {
    expect(transactionListPath(7, {
      accountId: 3,
      categoryId: 5,
      type: 'purchase',
      dateFrom: '2026-01-01',
      dateTo: '2026-01-31',
      includedInSpending: false,
      search: '  coffee shop  ',
      includeDeleted: true,
    })).toBe('/profiles/7/transactions?account_id=3&category_id=5&type=purchase&date_from=2026-01-01&date_to=2026-01-31&included_in_spending=false&search=coffee+shop&include_deleted=true');
  });

  it('keeps the unfiltered URL clean', () => {
    expect(transactionListPath(2, emptyFilters)).toBe('/profiles/2/transactions');
  });

  it('never carries previous-profile rows while the next profile loads', async () => {
    const pending = new Promise<never>(() => undefined);
    const get = vi.spyOn(client.api, 'get').mockResolvedValueOnce([]).mockReturnValueOnce(pending);
    const { result, rerender } = renderHook(({ profileId }) => useTransactions(profileId, emptyFilters), { initialProps: { profileId: 1 }, wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    rerender({ profileId: 2 });
    expect(result.current.data).toBeUndefined();
    expect(get).toHaveBeenLastCalledWith('/profiles/2/transactions');
  });
});
