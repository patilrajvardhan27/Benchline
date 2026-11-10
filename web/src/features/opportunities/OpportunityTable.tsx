import { Link } from "react-router-dom";
import type { Opportunity } from "../../shared/api/types";
import { formatInt, formatMoney, formatUnitPrice } from "../../shared/format/format";
import { type Column, DataTable } from "../../shared/ui/DataTable";

const COLUMNS: Column<Opportunity>[] = [
  { key: "item", header: "Product", render: (o) => <Link to={`/items/${o.itemId}`}>{o.description}</Link> },
  { key: "paid", header: "Paid per unit", numeric: true, render: (o) => formatUnitPrice(o.paidUnitPrice) },
  { key: "p25", header: "Group p25", numeric: true, render: (o) => formatUnitPrice(o.benchmarkP25) },
  { key: "qty", header: "Units", numeric: true, render: (o) => formatInt(o.qty) },
  { key: "save", header: "Potential saving", numeric: true, render: (o) => formatMoney(o.savingsAmount) },
];

export function OpportunityTable({ lines }: { lines: Opportunity[] }) {
  return <DataTable caption="Synthetic purchase lines priced above the group p25" columns={COLUMNS} rows={lines} getRowKey={(o) => String(o.purchaseLineId)} />;
}
