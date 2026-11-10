import type { Anomaly, BenchmarkSnapshot, PricePoint } from "../../shared/api/types";
import { formatChange, formatDate, formatUnitPrice } from "../../shared/format/format";
import { type Column, DataTable } from "../../shared/ui/DataTable";
import { type ChartSeries, LineChart } from "../../shared/ui/LineChart";

interface Props {
  prices: PricePoint[];
  benchmark?: BenchmarkSnapshot;
  flagged?: Anomaly[];
}

const dollars = (v: number) => `$${v >= 1 ? v.toFixed(2) : v.toFixed(3)}`;

export function PriceHistory({ prices, benchmark, flagged = [] }: Props) {
  if (prices.length === 0) return <p>No price history is stored for this product yet.</p>;
  const flaggedIds = new Set(flagged.map((a) => a.pricePointId));
  const series: ChartSeries[] = [{
    id: "price", step: true,
    points: prices.map((p) => ({ date: p.effectiveDate, value: Number(p.unitPrice), flagged: flaggedIds.has(p.id) })),
  }];
  const first = prices[0];
  const last = prices[prices.length - 1];
  const label = `NADAC price per unit from ${formatDate(first?.effectiveDate)} to ${formatDate(last?.effectiveDate)}, ${prices.length} changes, latest ${formatUnitPrice(last?.unitPrice)}`;

  const rows = [...prices].reverse().map((p, i, all) => ({ ...p, previous: all[i + 1]?.unitPrice }));
  const columns: Column<(typeof rows)[number]>[] = [
    { key: "d", header: "Effective", render: (r) => formatDate(r.effectiveDate) },
    { key: "p", header: "Price per unit", numeric: true, render: (r) => formatUnitPrice(r.unitPrice) },
    { key: "c", header: "Change", numeric: true, render: (r) => formatChange(r.unitPrice, r.previous) },
    { key: "a", header: "Published", render: (r) => formatDate(r.asOfDate) },
  ];

  return (
    <div className="stack">
      <LineChart series={series} ariaLabel={label} formatY={dollars}
        band={benchmark ? { low: Number(benchmark.p25), high: Number(benchmark.p75), label: "Group p25 to p75" } : undefined} />
      <details>
        <summary>View the same data as a table</summary>
        <DataTable caption="Price changes, newest first" columns={columns} rows={rows} getRowKey={(r) => r.id} />
      </details>
    </div>
  );
}
