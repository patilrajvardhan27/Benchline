import { useSearchParams } from "react-router-dom";
import { ItemSearch } from "../features/items/ItemSearch";
import { ItemsTable } from "../features/items/ItemsTable";
import type { ItemPage } from "../shared/api/types";
import { useApiQuery } from "../shared/api/useApiQuery";
import { useDebounce } from "../shared/hooks/useDebounce";
import { Async } from "../shared/ui/Async";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageShell } from "../shared/ui/PageShell";
import { Pagination } from "../shared/ui/Pagination";
import { Skeleton } from "../shared/ui/Skeleton";

const SIZE = 25;

export function ItemsPage() {
  const [params, setParams] = useSearchParams();
  const text = params.get("q") ?? "";
  const page = Math.max(Number(params.get("page") ?? 0) || 0, 0);
  const debounced = useDebounce(text);

  const query = useApiQuery<ItemPage>("/api/v1/items", { query: { query: debounced, page, size: SIZE } });

  const update = (next: { q?: string; page?: number }) => {
    const copy = new URLSearchParams(params);
    if (next.q !== undefined) { if (next.q) copy.set("q", next.q); else copy.delete("q"); copy.delete("page"); }
    if (next.page !== undefined) { if (next.page > 0) copy.set("page", String(next.page)); else copy.delete("page"); }
    setParams(copy, { replace: true });
  };

  return (
    <PageShell title="Items" description="Every NDC with a stored NADAC price, newest rate shown.">
      <ItemSearch value={text} onChange={(q) => { update({ q }); }} />
      <Async query={query} loading={<Skeleton variant="row" count={8} />}>
        {(data) =>
          data.content.length === 0 ? (
            <EmptyState title="No products found">
              <p>Try a shorter name, or the first digits of an NDC.</p>
            </EmptyState>
          ) : (
            <>
              <ItemsTable items={data.content} />
              <Pagination page={data.page} onChange={(p) => { update({ page: p }); }} />
            </>
          )
        }
      </Async>
    </PageShell>
  );
}
