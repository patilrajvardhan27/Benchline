import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ErrorState } from "./ErrorState";

interface Props<T> {
  query: UseQueryResult<T>;
  loading: ReactNode;
  children: (data: T) => ReactNode;
}

/** Loading, error and success in one place so every page handles all three. */
export function Async<T>({ query, loading, children }: Props<T>) {
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (query.data === undefined) {
    return <div aria-busy="true" aria-live="polite"><span className="visually-hidden">Loading</span>{loading}</div>;
  }
  return <>{children(query.data)}</>;
}
