import { create } from "zustand";
import { AgentRunError, type AgentRunner, DroppedStreamError, streamAgentRun } from "./client";
import type { AgentEvent, Citation } from "./events";

export type TurnStatus = "streaming" | "done" | "cancelled" | "error" | "dropped";

export type Step =
  | { kind: "thinking"; id: string; text: string }
  | {
      kind: "tool"; id: string; name: string; label: string; arguments: string;
      result: { ok: boolean; summary: string; citations: Citation[] } | null;
    };

export interface Turn {
  id: string;
  question: string;
  steps: Step[];
  answer: { text: string; citations: Citation[] } | null;
  status: TurnStatus;
  error: string | null;
  retryable: boolean;
  stats: { steps: number; tokens: number } | null;
  recorded: boolean;
}

interface RunDeps {
  token: string | null;
  recorded: boolean;
  run?: AgentRunner;
  paceMs?: number;
}

interface AgentState {
  turns: Turn[];
  activeId: string | null;
  ask: (question: string, deps: RunDeps) => string;
  retry: (id: string, deps: RunDeps) => void;
  cancel: () => void;
  applyEvent: (id: string, event: AgentEvent) => void;
  finish: (id: string, status: TurnStatus, error?: AgentRunError) => void;
  clear: () => void;
}

// Abort handles are not state: nothing renders from them and they cannot be serialised.
const controllers = new Map<string, AbortController>();
let counter = 0;

const blank = (id: string, question: string, recorded: boolean): Turn => ({
  id, question, steps: [], answer: null, status: "streaming", error: null, retryable: false, stats: null, recorded,
});

/** Pure: one event applied to one turn. Unit-tested without React or a network. */
export function reduceTurn(turn: Turn, event: AgentEvent): Turn {
  switch (event.type) {
    case "thinking":
      return { ...turn, steps: [...turn.steps, { kind: "thinking", id: `t${turn.steps.length}`, text: event.data.text }] };
    case "tool_call": {
      const { call_id, name, label, arguments: args } = event.data;
      return { ...turn, steps: [...turn.steps, { kind: "tool", id: call_id, name, label, arguments: args, result: null }] };
    }
    case "tool_result": {
      const { call_id, ok, summary, citations } = event.data;
      const steps = turn.steps.map((s) => (s.kind === "tool" && s.id === call_id ? { ...s, result: { ok, summary, citations } } : s));
      return { ...turn, steps };
    }
    case "answer":
      return { ...turn, answer: event.data };
    case "error":
      return { ...turn, status: "error", error: event.data.message, retryable: event.data.retryable };
    case "done":
      return { ...turn, status: "done", stats: { steps: event.data.steps, tokens: event.data.tokens } };
    default:
      return turn;
  }
}

export const useAgentStore = create<AgentState>()((set, get) => {
  const update = (id: string, change: (turn: Turn) => Turn) =>
    set((s) => ({ turns: s.turns.map((t) => (t.id === id ? change(t) : t)) }));

  async function start(id: string, deps: RunDeps) {
    controllers.get(id)?.abort();
    const controller = new AbortController();
    controllers.set(id, controller);
    const turn = get().turns.find((t) => t.id === id);
    if (!turn) return;
    const run = deps.run ?? streamAgentRun;
    try {
      for await (const event of run(turn.question, { token: deps.token, signal: controller.signal, paceMs: deps.paceMs })) {
        // Cancel wins even if the stream has more events buffered.
        if (controller.signal.aborted) break;
        get().applyEvent(id, event);
      }
      if (controller.signal.aborted) get().finish(id, "cancelled");
    } catch (error) {
      if (controller.signal.aborted) get().finish(id, "cancelled");
      else if (error instanceof DroppedStreamError) get().finish(id, "dropped", error);
      else get().finish(id, "error", error instanceof AgentRunError ? error : new AgentRunError("Something went wrong.", true));
    } finally {
      if (controllers.get(id) === controller) controllers.delete(id);
    }
  }

  return {
    turns: [],
    activeId: null,
    ask: (question, deps) => {
      get().cancel();
      const id = `turn-${++counter}`;
      set((s) => ({ turns: [...s.turns, blank(id, question.trim(), deps.recorded)], activeId: id }));
      void start(id, deps);
      return id;
    },
    retry: (id, deps) => {
      get().cancel();
      update(id, (t) => blank(t.id, t.question, deps.recorded));
      set({ activeId: id });
      void start(id, deps);
    },
    cancel: () => {
      const id = get().activeId;
      if (!id) return;
      controllers.get(id)?.abort();
      get().finish(id, "cancelled"); // at once, even if the stream is stuck waiting on the network
    },
    applyEvent: (id, event) => update(id, (t) => reduceTurn(t, event)),
    finish: (id, status, error) =>
      update(id, (t) => (t.status !== "streaming" ? t : {
        ...t, status, error: error?.message ?? null, retryable: status === "cancelled" || (error?.retryable ?? false),
      })),
    clear: () => {
      get().cancel();
      set({ turns: [], activeId: null });
    },
  };
});

type State = ReturnType<typeof useAgentStore.getState>;

export const selectActiveTurn = (s: State): Turn | null => s.turns.find((t) => t.id === s.activeId) ?? null;

export const selectIsRunning = (s: State): boolean => selectActiveTurn(s)?.status === "streaming";

/** What a skeleton should stand in for: a tool still running, the next step, or nothing. */
export function pendingStep(turn: Turn): "tool" | "next" | null {
  if (turn.status !== "streaming" || turn.answer) return null;
  const last = turn.steps.at(-1);
  return last?.kind === "tool" && !last.result ? "tool" : "next";
}

export const toolCallCount = (turn: Turn): number => turn.steps.filter((s) => s.kind === "tool").length;

/** One short sentence for the live region, so a screen reader hears progress, not the whole trace. */
export function selectAnnouncement(s: State): string {
  const turn = selectActiveTurn(s);
  if (!turn) return "";
  switch (turn.status) {
    case "done": return "Answer ready.";
    case "cancelled": return "Question cancelled.";
    case "dropped": return "The connection dropped. You can retry.";
    case "error": return turn.error ?? "Something went wrong.";
  }
  const last = turn.steps.at(-1);
  if (turn.answer) return "Writing the answer.";
  if (last?.kind === "tool") return last.result ? `Found: ${last.result.summary}` : `Looking up: ${last.label}`;
  return last ? "Thinking." : "Working on your question.";
}
