import { type SyntheticEvent, useId, useState } from "react";
import { useAuth } from "../../shared/api/auth";
import { config } from "../../shared/config";
import { AgentTurn } from "./AgentTurn";
import type { AgentRunner } from "./client";
import { selectAnnouncement, selectIsRunning, useAgentStore } from "./store";

// The first two have recordings, so they also work in the public demo.
export const SUGGESTIONS = [
  "Is $0.06 per tablet a fair price for sertraline 50 mg?",
  "Have there been any unusual price moves for omeprazole 20 mg?",
  ...(config.demoMode ? [] : ["Which metformin 500 mg products are cheapest?"]),
];

// Timing, not motion: a replay paced like a live run shows each step arriving.
const REPLAY_PACE_MS = 450;

/** Tests pass a runner; the app uses the real stream. */
export function AgentPanel({ run }: { run?: AgentRunner }) {
  const [question, setQuestion] = useState("");
  const turns = useAgentStore((s) => s.turns);
  const running = useAgentStore(selectIsRunning);
  const announcement = useAgentStore(selectAnnouncement);
  const { ask, retry, cancel } = useAgentStore.getState();
  const { status, token, signIn } = useAuth();
  const inputId = useId();
  const hintId = useId();

  const canAsk = status === "demo" || status === "authenticated";
  const deps = { token, run, recorded: config.demoMode, paceMs: config.demoMode ? REPLAY_PACE_MS : 0 };

  const submit = (text: string) => {
    if (!text.trim() || running || !canAsk) return;
    ask(text, deps);
    setQuestion("");
  };
  const onSubmit = (e: SyntheticEvent) => {
    e.preventDefault();
    submit(question);
  };

  return (
    <div className="agent-panel">
      {config.demoMode && (
        <div className="banner banner--info">
          <p>
            <strong>Recorded runs.</strong> The public demo has no live model. It replays streams recorded from the
            agent&apos;s own endpoint over this snapshot, for the suggested questions. The full stack answers any question.
          </p>
        </div>
      )}
      {!canAsk && (
        <div className="banner banner--info">
          <p>Sign in to ask questions. The assistant reads prices and flags; it cannot change anything.</p>
          {status === "anonymous" && (
            <button type="button" className="btn" onClick={() => void signIn()}>Sign in</button>
          )}
        </div>
      )}

      <form className="agent-form" onSubmit={onSubmit}>
        <label htmlFor={inputId}>Your question</label>
        <p id={hintId} className="hint">Ask about a drug&apos;s fair price, its equivalents or unusual price moves.</p>
        <div className="agent-form__row">
          <input
            id={inputId} type="text" value={question} maxLength={500} autoComplete="off"
            aria-describedby={hintId} disabled={!canAsk}
            onChange={(e) => setQuestion(e.target.value)}
          />
          {running ? (
            <button type="button" className="btn btn--danger" onClick={cancel}>Cancel</button>
          ) : (
            <button type="submit" className="btn" disabled={!canAsk || question.trim().length < 3}>Ask</button>
          )}
        </div>
      </form>

      <div className="agent-suggestions" role="group" aria-label="Suggested questions">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" className="btn btn--quiet" disabled={running || !canAsk} onClick={() => submit(s)}>
            {s}
          </button>
        ))}
      </div>

      {turns.length > 0 && (
        <ol className="agent-turns" aria-label="Conversation">
          {turns.map((turn) => <AgentTurn key={turn.id} turn={turn} onRetry={(id) => retry(id, deps)} />)}
        </ol>
      )}

      <p className="visually-hidden" role="status" aria-live="polite">{announcement}</p>
    </div>
  );
}
