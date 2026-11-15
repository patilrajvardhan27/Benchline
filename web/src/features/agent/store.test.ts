import { DroppedStreamError, type AgentRunner } from "./client";
import type { AgentEvent } from "./events";
import {
  pendingStep, reduceTurn, selectActiveTurn, selectAnnouncement, selectIsRunning, toolCallCount, type Turn, useAgentStore,
} from "./store";

const CITE = { item_id: "ndc-00000000001", label: "ATORVASTATIN 20 MG TAB (NDC 00000000001)" };
const RUN: AgentEvent[] = [
  { type: "run", data: { run_id: "r1" } },
  { type: "thinking", data: { text: "Checking the benchmark." } },
  { type: "tool_call", data: { call_id: "c1", name: "get_benchmark", arguments: '{"drug":"atorvastatin"}', label: "Benchmark for atorvastatin" } },
  { type: "tool_result", data: { call_id: "c1", name: "get_benchmark", ok: true, summary: "median $0.03", citations: [CITE] } },
  { type: "answer", data: { text: "Fair.", citations: [CITE] } },
  { type: "done", data: { steps: 2, tokens: 10, cost_usd: 0 } },
];

const blank: Turn = { id: "t", question: "q", steps: [], answer: null, status: "streaming", error: null, retryable: false, stats: null, recorded: false };

function runner(events: AgentEvent[], end?: Error, delayMs = 1): AgentRunner {
  return async function* (_question, { signal }) {
    for (const e of events) {
      await new Promise((r) => setTimeout(r, delayMs));
      if (signal.aborted) throw new DOMException("Aborted", "AbortError");
      yield e;
    }
    if (end) throw end;
  };
}

const settle = () => vi.waitFor(() => expect(selectIsRunning(useAgentStore.getState())).toBe(false));

beforeEach(() => useAgentStore.getState().clear());

describe("reduceTurn and selectors", () => {
  it("builds the trace step by step", () => {
    const states = RUN.reduce<Turn[]>((acc, e) => [...acc, reduceTurn(acc.at(-1) ?? blank, e)], []);
    const [, thinking, afterCall, afterResult, , final] = states as [Turn, Turn, Turn, Turn, Turn, Turn];
    expect(pendingStep(thinking)).toBe("next");
    expect(pendingStep(afterCall)).toBe("tool");
    expect(afterResult.steps[1]).toMatchObject({ kind: "tool", result: { ok: true, summary: "median $0.03" } });
    expect(final).toMatchObject({ status: "done", answer: { text: "Fair." }, stats: { steps: 2, tokens: 10 } });
    expect(pendingStep(final)).toBeNull();
    expect(toolCallCount(final)).toBe(1);
  });

  it("an error event ends the turn with the server's message", () => {
    const t = reduceTurn(blank, { type: "error", data: { message: "Stopped after 6 steps.", retryable: false } });
    expect(t).toMatchObject({ status: "error", error: "Stopped after 6 steps.", retryable: false });
  });
});

describe("the store", () => {
  it("runs a question to the end and announces it", async () => {
    useAgentStore.getState().ask("Is atorvastatin fair?", { token: null, recorded: false, run: runner(RUN) });
    expect(selectAnnouncement(useAgentStore.getState())).toBe("Working on your question.");
    await settle();
    expect(selectActiveTurn(useAgentStore.getState())).toMatchObject({ status: "done", question: "Is atorvastatin fair?" });
    expect(selectAnnouncement(useAgentStore.getState())).toBe("Answer ready.");
  });

  it("cancel stops the run and allows a retry", async () => {
    const { ask, cancel } = useAgentStore.getState();
    ask("q1", { token: null, recorded: false, run: runner(RUN, undefined, 30) });
    await vi.waitFor(() => expect(selectActiveTurn(useAgentStore.getState())?.steps.length).toBeGreaterThan(0));
    cancel();
    expect(selectActiveTurn(useAgentStore.getState())).toMatchObject({ status: "cancelled", retryable: true });
    await new Promise((r) => setTimeout(r, 200));   // late events from the stream change nothing
    expect(selectActiveTurn(useAgentStore.getState())).toMatchObject({ status: "cancelled", answer: null });
  });

  it("a dropped stream can be retried into a full answer", async () => {
    const { ask, retry } = useAgentStore.getState();
    const id = ask("q", { token: null, recorded: false, run: runner(RUN.slice(0, 3), new DroppedStreamError()) });
    await settle();
    expect(selectActiveTurn(useAgentStore.getState())).toMatchObject({ status: "dropped", retryable: true, steps: [{}, {}] });

    retry(id, { token: null, recorded: false, run: runner(RUN) });
    await settle();
    const turn = selectActiveTurn(useAgentStore.getState());
    expect(turn?.status).toBe("done");
    expect(turn?.steps).toHaveLength(2);           // replaced, not appended to the dropped attempt
    expect(useAgentStore.getState().turns).toHaveLength(1);
  });

  it("asking again keeps the earlier turns", async () => {
    const { ask } = useAgentStore.getState();
    ask("first", { token: null, recorded: false, run: runner(RUN) });
    await settle();
    ask("second", { token: null, recorded: false, run: runner(RUN) });
    await settle();
    expect(useAgentStore.getState().turns.map((t) => t.question)).toEqual(["first", "second"]);
  });
});
