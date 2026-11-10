import type { ReactNode } from "react";
import { Skeleton } from "./Skeleton";

export interface Stat {
  label: string;
  value: ReactNode;
}

/** A row of headline numbers. Plain definition list, not a set of feature cards. */
export function StatStrip({ stats, loading = false }: { stats: Stat[]; loading?: boolean }) {
  return (
    <dl className="stat-strip" aria-busy={loading}>
      {stats.map((stat) => (
        <div key={stat.label}>
          <dt>{stat.label}</dt>
          <dd>{loading ? <Skeleton variant="stat" /> : stat.value}</dd>
        </div>
      ))}
    </dl>
  );
}
