import { vi } from "vitest";
import { AgentRunError, DroppedStreamError, streamAgentRun } from "./client";
import { type AgentEvent, toAgentEvent } from "./events";
import { parseBlock, readSse } from "./sse";
// The files the public demo serves.
import INDEX from "../../../public/demo/agent/index.json?raw";
import RECORDING from "../../../public/demo/agent/fair-price-sertraline.sse?raw";

const QUESTION = "Is $0.06 per tablet a fair price for sertraline 50 mg?";

/** A body that arrives in the given pieces, like a slow network. */
function chunked(...pieces: (string | Uint8Array)[]) {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const p of pieces) controller.enqueue(typeof p === "string" ? encoder.encode(p) : p);
      controller.close();
    },
  });
}

async function all<T>(source: AsyncIterable<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const x of source) out.push(x);
  return out;
}

describe("readSse", () => {
  it("joins events split across chunks, mid-line and mid-character", async () => {
    const bytes = new TextEncoder().encode('event: thinking\ndata: {"text":"café"}\n\n');
    const split = bytes.indexOf(0xc3) + 1; // inside the two-byte "é"
    const messages = await all(readSse(chunked(bytes.slice(0, 9), bytes.slice(9, split), bytes.slice(split))));
    expect(messages).toEqual([{ id: null, event: "thinking", data: '{"text":"café"}' }]);
  });

  it("handles CRLF, comments and multi-line data", async () => {
    const messages = await all(readSse(chunked(": keep-alive\r\n\r\nid: 3\r\nevent: x\r\ndata: a\r\ndata: b\r\n\r\n")));
    expect(messages).toEqual([{ id: "3", event: "x", data: "a\nb" }]);
  });

  it("skips blocks with no data", () => {
    expect(parseBlock(": just a comment")).toBeNull();
  });
});

describe("toAgentEvent", () => {
  it("accepts events that match the contract", () => {
    expect(toAgentEvent({ id: "1", event: "thinking", data: '{"text":"hi"}' })).toEqual({ type: "thinking", data: { text: "hi" } });
  });

  it("drops unknown types, bad JSON and unsafe item ids", () => {
    expect(toAgentEvent({ id: null, event: "debug", data: "{}" })).toBeNull();
    expect(toAgentEvent({ id: null, event: "thinking", data: "not json" })).toBeNull();
    const evil = JSON.stringify({ text: "x", citations: [{ item_id: "../../admin", label: "x" }] });
    expect(toAgentEvent({ id: null, event: "answer", data: evil })).toBeNull();
  });
});

describe("streamAgentRun in the public demo", () => {
  function serve(sse: string | ReadableStream<Uint8Array>) {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve(
      url.endsWith("index.json") ? new Response(INDEX) : new Response(sse),
    )));
  }

  it("replays the recording that matches the question", async () => {
    serve(RECORDING);
    const events: AgentEvent[] = await all(streamAgentRun(`  ${QUESTION.toUpperCase()} `, { token: null, signal: new AbortController().signal }));
    expect(events.map((e) => e.type)).toEqual([
      "run", "thinking", "tool_call", "tool_result", "tool_call", "tool_result", "thinking", "tool_call", "tool_result", "answer", "done",
    ]);
  });

  it("calls a stream that ends without done a dropped stream", async () => {
    serve(RECORDING.slice(0, RECORDING.indexOf("event: answer")));
    await expect(all(streamAgentRun(QUESTION, { token: null, signal: new AbortController().signal })))
      .rejects.toBeInstanceOf(DroppedStreamError);
  });

  it("refuses questions it has no recording for", async () => {
    serve(RECORDING);
    await expect(all(streamAgentRun("What is the meaning of life?", { token: null, signal: new AbortController().signal })))
      .rejects.toThrow(AgentRunError);
  });

  it("stops when aborted between paced events", async () => {
    serve(RECORDING);
    const controller = new AbortController();
    const seen: string[] = [];
    const run = (async () => {
      for await (const e of streamAgentRun(QUESTION, { token: null, signal: controller.signal, paceMs: 20 })) seen.push(e.type);
    })();
    setTimeout(() => controller.abort(), 50);
    await expect(run).rejects.toMatchObject({ name: "AbortError" });
    expect(seen.length).toBeGreaterThan(0);
    expect(seen).not.toContain("done");
  });
});
