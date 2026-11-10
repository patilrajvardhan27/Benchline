import { Link } from "react-router-dom";
import type { Anomaly } from "../../shared/api/types";
import { formatChange, formatDate, formatUnitPrice } from "../../shared/format/format";
import { Badge } from "../../shared/ui/Badge";
import { type Column, DataTable } from "../../shared/ui/DataTable";

interface Props {
  rows: Anomaly[];
  canReview: boolean;
  pendingId?: string;
  onReview: (id: string, status: "CONFIRMED" | "DISMISSED") => void;
}

const tone = { OPEN: "ember", CONFIRMED: "teal", DISMISSED: "muted" } as const;

export function AnomalyTable({ rows, canReview, pendingId, onReview }: Props) {
  const columns: Column<Anomaly>[] = [
    {
      key: "g", header: "Product",
      render: (a) => (
        <>
          <Link to={`/items/${a.itemId}`}>{a.groupName}</Link>
          <br />
          <span className="mono muted">NDC {a.itemId.replace(/^ndc-/, "")}</span>
        </>
      ),
    },
    { key: "d", header: "Effective", render: (a) => formatDate(a.effectiveDate) },
    { key: "p", header: "Price change", numeric: true, render: (a) => `${formatUnitPrice(a.previousUnitPrice)} to ${formatUnitPrice(a.unitPrice)} (${formatChange(a.unitPrice, a.previousUnitPrice)})` },
    { key: "s", header: "Score", numeric: true, render: (a) => a.score.toFixed(1) },
    { key: "st", header: "Status", render: (a) => <Badge tone={tone[a.status]}>{a.status.toLowerCase()}</Badge> },
    {
      key: "act", header: "Review",
      render: (a) => a.status !== "OPEN" ? null : (
        <span className="cluster">
          <button type="button" className="btn btn--quiet" disabled={!canReview || pendingId === a.id}
            onClick={() => { onReview(a.id, "CONFIRMED"); }}>Confirm<span className="visually-hidden"> {a.groupName}</span></button>
          <button type="button" className="btn btn--danger" disabled={!canReview || pendingId === a.id}
            onClick={() => { onReview(a.id, "DISMISSED"); }}>Dismiss<span className="visually-hidden"> {a.groupName}</span></button>
        </span>
      ),
    },
  ];
  return <DataTable caption="Price changes flagged as unusual, highest score first" columns={columns} rows={rows} getRowKey={(a) => a.id} />;
}
