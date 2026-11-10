import { useId, useState } from "react";
import { OpportunityTable } from "../features/opportunities/OpportunityTable";
import type { Facility, OpportunityReport } from "../shared/api/types";
import { useApiQuery } from "../shared/api/useApiQuery";
import { formatMoney } from "../shared/format/format";
import { Async } from "../shared/ui/Async";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageShell } from "../shared/ui/PageShell";
import { Pagination } from "../shared/ui/Pagination";
import { RequireAccess } from "../shared/ui/RequireAccess";
import { Skeleton } from "../shared/ui/Skeleton";
import { StatStrip } from "../shared/ui/StatStrip";
import { SyntheticBanner } from "../shared/ui/SyntheticBanner";

export function OpportunitiesPage() {
  return (
    <PageShell title="Savings opportunities"
      description="Purchases priced above the 25th percentile of their product group.">
      <SyntheticBanner />
      <RequireAccess><Picker /></RequireAccess>
    </PageShell>
  );
}

function Picker() {
  const id = useId();
  const facilities = useApiQuery<Facility[]>("/api/v1/members", { protectedResource: true });
  const [chosen, setChosen] = useState<string>("");
  const [page, setPage] = useState(0);
  const memberId = chosen || facilities.data?.[0]?.id || "";

  return (
    <Async query={facilities} loading={<Skeleton variant="row" count={4} />}>
      {(list) => (
        <div className="stack">
          <div className="field">
            <label htmlFor={id}>Facility (synthetic)</label>
            <select id={id} value={memberId} onChange={(e) => { setChosen(e.target.value); setPage(0); }}>
              {list.map((f) => <option key={f.id} value={f.id}>{f.name}, {f.bedBand} beds, {f.region}</option>)}
            </select>
          </div>
          {memberId && <Report memberId={memberId} page={page} onPage={setPage} />}
        </div>
      )}
    </Async>
  );
}

function Report({ memberId, page, onPage }: { memberId: string; page: number; onPage: (p: number) => void }) {
  const report = useApiQuery<OpportunityReport>(`/api/v1/members/${memberId}/opportunities`,
    { protectedResource: true, query: { page, size: 20 } });
  return (
    <Async query={report} loading={<Skeleton variant="row" count={8} />}>
      {(data) => (
        <div className="stack">
          <StatStrip stats={[
            { label: "Potential saving, all lines", value: formatMoney(data.totalSavings) },
            { label: "Lines above p25", value: data.page.totalElements },
          ]} />
          {data.lines.length === 0
            ? <EmptyState title="Nothing above benchmark"><p>Every purchase line is at or below its group p25.</p></EmptyState>
            : <><OpportunityTable lines={data.lines} /><Pagination page={data.page} onChange={onPage} /></>}
        </div>
      )}
    </Async>
  );
}
