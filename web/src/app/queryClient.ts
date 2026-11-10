import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "../shared/api/errors";

const MAX_RETRIES = 2;

/** Retry only what might succeed later: network failures and 5xx. A 404 or 403 will not change. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false;
  if (error instanceof ApiError) return error.status === 0 || error.status >= 500;
  return false;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 60_000, retry: shouldRetry, refetchOnWindowFocus: false },
    },
  });
}
