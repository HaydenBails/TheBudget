import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './client';

/** Shared TanStack Query client for the production app. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't hammer a local API; one retry, but never retry validation errors.
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return failureCount < 1;
      },
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
});
