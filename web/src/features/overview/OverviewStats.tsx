import type { Overview } from "../../shared/api/types";
import { useApiQuery } from "../../shared/api/useApiQuery";
import { AnimatedNumber } from "../../shared/ui/AnimatedNumber";
import { ErrorState } from "../../shared/ui/ErrorState";
import { StatStrip } from "../../shared/ui/StatStrip";
import { formatDate } from "../../shared/format/format";

export function OverviewStats() {
  const query = useApiQuery<Overview>("/api/v1/overview");
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const data = query.data;
  return (
    <StatStrip
      loading={!data}
      stats={[
        { label: "Products (NDCs)", value: data && <AnimatedNumber value={data.itemCount} /> },
        { label: "Product groups", value: data && <AnimatedNumber value={data.groupCount} /> },
        { label: "Price changes stored", value: data && <AnimatedNumber value={data.pricePointCount} /> },
        { label: "Latest CMS publication", value: data && <span style={{ fontSize: "var(--bl-text-lg)" }}>{formatDate(data.latestAsOfDate)}</span> },
      ]}
    />
  );
}
