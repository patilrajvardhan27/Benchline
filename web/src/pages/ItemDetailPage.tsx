import { Link, useParams } from "react-router-dom";
import { BenchmarkRange } from "../features/benchmarks/BenchmarkRange";
import { Equivalents } from "../features/items/Equivalents";
import { PriceHistory } from "../features/items/PriceHistory";
import type { Anomaly, AnomalyPage, BenchmarkSnapshot, Equivalent, Item, PricePoint } from "../shared/api/types";
import { useApiQuery } from "../shared/api/useApiQuery";
import { formatChange, formatDate, formatUnitPrice } from "../shared/format/format";
import { Async } from "../shared/ui/Async";
import { Badge } from "../shared/ui/Badge";
import { PageShell } from "../shared/ui/PageShell";
import { Skeleton } from "../shared/ui/Skeleton";
import { StatStrip } from "../shared/ui/StatStrip";

export function ItemDetailPage() {
  const { itemId = "" } = useParams();
  const item = useApiQuery<Item>(`/api/v1/items/${itemId}`);

  return (
    <Async query={item} loading={<PageShell title="Loading product" focusOnMount={false}><Skeleton variant="stat" /><Skeleton variant="chart" /></PageShell>}>
      {(data) => <Detail item={data} />}
    </Async>
  );
}

function Detail({ item }: { item: Item }) {
  const prices = useApiQuery<PricePoint[]>(`/api/v1/items/${item.id}/prices`, { query: { source: "NADAC" } });
  const benchmark = useApiQuery<BenchmarkSnapshot>(`/api/v1/benchmarks/groups/${item.groupId}`);
  const equivalents = useApiQuery<Equivalent[]>(`/api/v1/items/${item.id}/equivalents`);
  const anomalies = useApiQuery<AnomalyPage>("/api/v1/anomalies", { protectedResource: true, query: { status: "OPEN", size: 100 } });
  const flagged: Anomaly[] = anomalies.data?.content.filter((a) => a.itemId === item.id) ?? [];

  const bm = benchmark.data;
  const above = bm && item.latestPrice ? Number(item.latestPrice) > Number(bm.p50) : undefined;
  const last = prices.data?.at(-1);
  const prev = prices.data?.at(-2);

  return (
    <PageShell title={item.description} description={`NDC ${item.ndc11}`}>
      <div className="stack">
        <p><Link to={`/items?q=${encodeURIComponent(item.description.split(" ")[0] ?? "")}`}>Back to search</Link></p>
        <StatStrip stats={[
          { label: "Latest price per unit", value: formatUnitPrice(item.latestPrice) },
          { label: "Group median (p50)", value: bm ? formatUnitPrice(bm.p50) : "n/a" },
          { label: "Versus median", value: bm && item.latestPrice ? formatChange(item.latestPrice, bm.p50) : "n/a" },
          { label: "Last change", value: <span style={{ fontSize: "var(--bl-text-lg)" }}>{last ? formatChange(last.unitPrice, prev?.unitPrice) : "n/a"}</span> },
        ]} />
        {above !== undefined && <p>{above ? <Badge tone="ember">Above group median</Badge> : <Badge tone="teal">At or below group median</Badge>}</p>}

        <section className="panel" aria-labelledby="bm-h">
          <h2 id="bm-h">Where this price sits in its group</h2>
          <Async query={benchmark} loading={<Skeleton variant="row" count={3} />}>
            {(b) => <BenchmarkRange benchmark={b} price={item.latestPrice} />}
          </Async>
        </section>

        <section className="panel" aria-labelledby="hist-h">
          <h2 id="hist-h">Price history</h2>
          <Async query={prices} loading={<Skeleton variant="chart" />}>
            {(rows) => <PriceHistory prices={rows} benchmark={bm} flagged={flagged} />}
          </Async>
          {flagged.length > 0 && <p className="muted">Orange markers are price moves flagged as unusual. Last published {formatDate(last?.asOfDate)}.</p>}
        </section>

        <section className="panel" aria-labelledby="eq-h">
          <h2 id="eq-h">Lower-priced equivalents</h2>
          <Async query={equivalents} loading={<Skeleton variant="row" count={3} />}>
            {(rows) => <Equivalents rows={rows} />}
          </Async>
          <p className="muted">Equivalents share this product's description. They are not checked for therapeutic equivalence.</p>
        </section>
      </div>
    </PageShell>
  );
}
