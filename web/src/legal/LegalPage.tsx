import type { ReactNode } from "react";
import { config } from "../shared/config";
import { PageShell } from "../shared/ui/PageShell";

/** Shared frame for the long-form legal pages. */
export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <PageShell title={title} description={`Last updated ${config.legalUpdated}`}>
      <div className="prose panel">{children}</div>
    </PageShell>
  );
}

export function Operator() {
  return <strong>{config.operatorName}</strong>;
}

export function ContactEmail() {
  return <a href={`mailto:${config.contactEmail}`}>{config.contactEmail}</a>;
}
