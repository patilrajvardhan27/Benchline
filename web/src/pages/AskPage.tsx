import { AgentPanel } from "../features/agent/AgentPanel";
import { PageShell } from "../shared/ui/PageShell";

export function AskPage() {
  return (
    <PageShell
      title="Ask Benchline"
      description="Ask about a drug's price. Every lookup is shown as it happens, and the answer links to the items it used."
    >
      <AgentPanel />
    </PageShell>
  );
}
