import { Link } from "react-router-dom";
import type { Equivalent } from "../../shared/api/types";
import { formatUnitPrice } from "../../shared/format/format";
import { type Column, DataTable } from "../../shared/ui/DataTable";

const COLUMNS: Column<Equivalent>[] = [
  { key: "ndc", header: "NDC", render: (e) => <Link to={`/items/${e.itemId}`} className="mono">{e.ndc11}</Link> },
  { key: "price", header: "Latest price", numeric: true, render: (e) => formatUnitPrice(e.latestPrice) },
  { key: "save", header: "Saves", numeric: true, render: (e) => formatUnitPrice(e.savingsPerUnit) },
];

export function Equivalents({ rows }: { rows: Equivalent[] }) {
  if (rows.length === 0) {
    return <p>No other product with the same description has a lower latest price.</p>;
  }
  return <DataTable caption="Lower-priced products with the same description (prices per unit)" columns={COLUMNS} rows={rows} getRowKey={(e) => e.itemId} />;
}
