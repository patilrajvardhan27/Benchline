import { Link } from "react-router-dom";
import type { Item } from "../../shared/api/types";
import { formatDate, formatUnitPrice } from "../../shared/format/format";
import { type Column, DataTable } from "../../shared/ui/DataTable";

const COLUMNS: Column<Item>[] = [
  { key: "name", header: "Product", render: (i) => <Link to={`/items/${i.id}`}>{i.description}</Link> },
  { key: "ndc", header: "NDC", render: (i) => <span className="mono">{i.ndc11}</span> },
  { key: "price", header: "Latest NADAC per unit", numeric: true, render: (i) => formatUnitPrice(i.latestPrice) },
  { key: "date", header: "Effective", render: (i) => formatDate(i.latestEffectiveDate) },
];

export function ItemsTable({ items }: { items: Item[] }) {
  return <DataTable caption="Products matching your search" columns={COLUMNS} rows={items} getRowKey={(i) => i.id} />;
}
