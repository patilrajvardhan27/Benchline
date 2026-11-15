import { vi } from "vitest";
import { AgentRunError, DroppedStreamError, streamAgentRun } from "./client";

vi.mock("../../shared/config", () => ({ config: { demoMode: false, agentBaseUrl: "https://api.example.test" } }));

const signal = () => new AbortController().signal;

async function drain(question = "Is 0.06 fair?") {
  const types: string[] = [];
  for await (const e of streamAgentRun(question, { token: "t0k3n", signal: signal() })) types.push(e.type);
  return types;
}

describe("streamAgentRun against the live service", () => {
  it("posts the question with the bearer token and no cookies", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response('event: answer\ndata: {"text":"ok","citations":[]}\n\nevent: done\ndata: {"steps":1,"tokens":5,"cost_usd":0}\n\n')));
    vi.stubGlobal("fetch", fetchMock);

    expect(await drain()).toEqual(["answer", "done"]);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://api.example.test/api/v1/agent/runs");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("omit");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer t0k3n");
    expect(JSON.parse(init.body as string)).toEqual({ question: "Is 0.06 fair?" });
  });

  it.each([
    [429, true, "several questions"],
    [503, true, "not available"],
    [401, false, "sign in"],
  ])("maps HTTP %i to a %s retry and a readable message", async (status, retryable, text) => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}", { status }))));
    const error = await drain().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(AgentRunError);
    expect((error as AgentRunError).retryable).toBe(retryable);
    expect((error as AgentRunError).message.toLowerCase()).toContain(text);
  });

  it("treats a network failure mid-stream as a dropped stream", async () => {
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(new TextEncoder().encode('event: thinking\ndata: {"text":"hm"}\n\n'));
        c.error(new TypeError("network error"));
      },
    });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(body))));
    await expect(drain()).rejects.toBeInstanceOf(DroppedStreamError);
  });

  it("reports an unreachable service as retryable", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
    await expect(drain()).rejects.toMatchObject({ retryable: true });
  });
});
