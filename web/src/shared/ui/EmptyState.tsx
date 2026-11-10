import type { ReactNode } from "react";

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="panel fade-in">
      <h2>{title}</h2>
      {children}
    </div>
  );
}
