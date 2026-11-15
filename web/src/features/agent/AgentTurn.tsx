import { Link } from "react-router-dom";
import { Skeleton } from "../../shared/ui/Skeleton";
import type { Citation } from "./events";
import { pendingStep, type Step, toolCallCount, type Turn } from "./store";

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function pretty(json: string): string {
  try {
    return JSON.stringify(JSON.parse(json), null, 2);
  } catch {
    return json;
  }
}

function Sources({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <ul className="agent-sources">
      {citations.map((c) => (
        // Built from the item id, never from a server-supplied URL.
        <li key={c.item_id}><Link to={`/items/${encodeURIComponent(c.item_id)}`}>{c.label}</Link></li>
      ))}
    </ul>
  );
}

function StepRow({ step }: { step: Step }) {
  if (step.kind === "thinking") {
    return <li className="agent-step agent-step--thinking"><p>{step.text}</p></li>;
  }
  const state = !step.result ? "running" : step.result.ok ? "ok" : "failed";
  return (
    <li className={`agent-step agent-step--tool agent-step--${state}`}>
      <details>
        <summary>
          <span className="agent-step__label">{step.label}</span>
          {step.result && <span className="agent-step__summary">{step.result.summary}</span>}
          {state === "failed" && <span className="badge badge--ember">failed</span>}
        </summary>
        <div className="agent-step__detail">
          <p className="agent-step__meta">Tool <code>{step.name}</code> called with</p>
          <pre>{pretty(step.arguments)}</pre>
          {step.result && <Sources citations={step.result.citations} />}
        </div>
      </details>
      {!step.result && <Skeleton variant="row" />}
    </li>
  );
}

const FOOTER: Record<Exclude<Turn["status"], "streaming" | "done">, string> = {
  cancelled: "You cancelled this question.",
  dropped: "The connection dropped before the answer finished.",
  error: "Something went wrong.",
};

interface Props {
  turn: Turn;
  onRetry: (id: string) => void;
}

export function AgentTurn({ turn, onRetry }: Props) {
  const pending = pendingStep(turn);
  const streaming = turn.status === "streaming";
  return (
    <li className="agent-turn" aria-busy={streaming}>
      <h2 className="agent-turn__question">{turn.question}</h2>
      {turn.steps.length > 0 && (
        <ol className="agent-trace" aria-label="Steps">
          {turn.steps.map((step) => <StepRow key={step.id} step={step} />)}
        </ol>
      )}
      {pending === "next" && <div className="agent-step agent-step--pending"><Skeleton variant="row" count={2} /></div>}
      {turn.answer && (
        <section className="agent-answer" aria-label="Answer">
          <p>{turn.answer.text}</p>
          {turn.answer.citations.length > 0 && <h3>Sources</h3>}
          <Sources citations={turn.answer.citations} />
        </section>
      )}
      {turn.status === "done" && (
        <p className="agent-turn__footer">
          {plural(turn.stats?.steps ?? 0, "step")}, {plural(toolCallCount(turn), "lookup")}.
          {turn.recorded && <> <span className="badge badge--muted">Recorded run</span></>}
        </p>
      )}
      {turn.status !== "streaming" && turn.status !== "done" && (
        <div className={`agent-turn__footer agent-turn__footer--${turn.status}`}>
          <p>{turn.status === "error" ? (turn.error ?? FOOTER.error) : FOOTER[turn.status]}</p>
          {turn.retryable && (
            <button type="button" className="btn btn--quiet" onClick={() => onRetry(turn.id)}>Retry</button>
          )}
        </div>
      )}
    </li>
  );
}
