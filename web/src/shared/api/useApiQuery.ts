import { type QueryKey, useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";
import type { QueryParams } from "./query";
import { useAuth } from "./auth";

interface Options {
  query?: QueryParams;
  /** Calls that need a signed-in user wait for a token (or demo mode). */
  protectedResource?: boolean;
  enabled?: boolean;
}

/** One way to read from the API: typed result, shared cache, auth handled for you. */
export function useApiQuery<T>(path: string, options: Options = {}) {
  const { query, protectedResource = false, enabled = true } = options;
  const { status, token } = useAuth();
  const allowed = !protectedResource || status === "demo" || status === "authenticated";
  const key: QueryKey = [path, query ?? {}, protectedResource ? token : null];
  return useQuery<T>({
    queryKey: key,
    queryFn: ({ signal }) => apiGet<T>(path, { query, token, signal }),
    enabled: enabled && allowed,
  });
}
