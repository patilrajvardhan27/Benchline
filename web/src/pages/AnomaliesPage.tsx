import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AnomalyTable } from "../features/anomalies/AnomalyTable";
import { apiPatch } from "../shared/api/client";
import { useAuth } from "../shared/api/auth";
import type { Anomaly, AnomalyPage, AnomalyStatus, FeatureConfig } from "../shared/api/types";
import { useApiQuery } from "../shared/api/useApiQuery";
import { config } from "../shared/config";
import { Async } from "../shared/ui/Async";
import { EmptyState } from "../shared/ui/EmptyState";
import { ErrorState } from "../shared/ui/ErrorState";
import { PageShell } from "../shared/ui/PageShell";
import { Pagination } from "../shared/ui/Pagination";
import { RequireAccess } from "../shared/ui/RequireAccess";
import { Skeleton } from "../shared/ui/Skeleton";

const TABS: { status: AnomalyStatus; label: string }[] = [
  { status: "OPEN", label: "Open" },
  { status: "CONFIRMED", label: "Confirmed" },
  { status: "DISMISSED", label: "Dismissed" },
];

export function AnomaliesPage() {
  const flags = useApiQuery<FeatureConfig>("/api/v1/config");
  const enabled = flags.data?.anomalyAlertsEnabled;
  return (
    <PageShell title="Anomaly review"
      description="Price moves far outside what is normal for their group, for a person to confirm or dismiss.">
      {enabled === false
        ? <EmptyState title="Anomaly alerts are switched off"><p>This feature is released behind a flag and is not enabled right now.</p></EmptyState>
        : <RequireAccess><Queue /></RequireAccess>}
    </PageShell>
  );
}

function Queue() {
  const [status, setStatus] = useState<AnomalyStatus>("OPEN");
  const [page, setPage] = useState(0);
  const { token, status: auth } = useAuth();
  const client = useQueryClient();
  const query = useApiQuery<AnomalyPage>("/api/v1/anomalies", { protectedResource: true, query: { status, page, size: 20 } });

  const review = useMutation({
    mutationFn: ({ id, next }: { id: string; next: "CONFIRMED" | "DISMISSED" }) =>
      apiPatch<Anomaly>(`/api/v1/anomalies/${id}`, { status: next }, { token }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["/api/v1/anomalies"] }),
  });

  return (
    <div className="stack">
      <div role="group" aria-label="Filter by status" className="cluster">
        {TABS.map((t) => (
          <button key={t.status} type="button" aria-pressed={status === t.status}
            className={status === t.status ? "btn" : "btn btn--quiet"}
            onClick={() => { setStatus(t.status); setPage(0); }}>{t.label}</button>
        ))}
      </div>
      {config.demoMode && <p className="muted">Reviewing is turned off in the public demo snapshot.</p>}
      {review.isError && <ErrorState error={review.error} />}
      <Async query={query} loading={<Skeleton variant="row" count={6} />}>
        {(data) => data.content.length === 0
          ? <EmptyState title={`No ${status.toLowerCase()} anomalies`}><p>Nothing to review here.</p></EmptyState>
          : <>
              <AnomalyTable rows={data.content} canReview={auth === "authenticated"}
                pendingId={review.isPending ? review.variables.id : undefined}
                onReview={(id, next) => { review.mutate({ id, next }); }} />
              <Pagination page={data.page} onChange={setPage} />
            </>}
      </Async>
    </div>
  );
}
