import { config } from "../../shared/config";
import { messageForStatus } from "../../shared/api/errors";
import { type AgentEvent, toAgentEvent } from "./events";
import { readSse } from "./sse";

export class AgentRunError extends Error {
  readonly retryable: boolean;

  constructor(message: string, retryable: boolean) {
    super(message);
    this.name = "AgentRunError";
    this.retryable = retryable;
  }
}

/** The stream ended, or broke, before the server said it was done. */
export class DroppedStreamError extends AgentRunError {
  constructor() {
    super("The connection dropped before the answer finished.", true);
    this.name = "DroppedStreamError";
  }
}

export interface RunOptions {
  token: string | null;
  signal: AbortSignal;
  /** Delay between replayed events, so a recording plays like a live run. */
  paceMs?: number;
}

export type AgentRunner = (question: string, options: RunOptions) => AsyncGenerator<AgentEvent>;

interface Recording {
  id: string;
  question: string;
  model: string;
}

const STATUS_TEXT: Record<number, string> = {
  429: "You have asked several questions in a row. Wait a minute and try again.",
  503: "The assistant is not available right now.",
};

const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

const normalise = (question: string) => question.trim().toLowerCase().replace(/\s+/g, " ");

async function loadRecordings(signal?: AbortSignal): Promise<Recording[]> {
  const response = await fetch("/demo/agent/index.json", { signal });
  return response.ok ? ((await response.json()) as Recording[]) : [];
}

async function openRecording(question: string, signal: AbortSignal): Promise<Response> {
  const match = (await loadRecordings(signal)).find((r) => normalise(r.question) === normalise(question));
  if (!match) {
    throw new AgentRunError("The public demo replays recorded runs of the suggested questions only.", false);
  }
  return fetch(`/demo/agent/${match.id}.sse`, { signal });
}

async function openLive(question: string, { token, signal }: RunOptions): Promise<Response> {
  return fetch(`${config.agentBaseUrl}/api/v1/agent/runs`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question }),
    signal,
    credentials: "omit",
  });
}

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    }, { once: true });
  });

/** Streams one run: live from the ML service, or replayed from a recording in the public demo. */
export async function* streamAgentRun(question: string, options: RunOptions): AsyncGenerator<AgentEvent> {
  let response: Response;
  try {
    response = config.demoMode ? await openRecording(question, options.signal) : await openLive(question, options);
  } catch (error) {
    if (isAbort(error) || error instanceof AgentRunError) throw error;
    throw new AgentRunError("The assistant could not be reached. Check your connection and try again.", true);
  }
  if (!response.ok || !response.body) {
    const status = response.status;
    throw new AgentRunError(STATUS_TEXT[status] ?? messageForStatus(status), status === 429 || status >= 500);
  }

  let finished = false;
  try {
    for await (const message of readSse(response.body)) {
      const event = toAgentEvent(message);
      if (!event) continue;
      if (options.paceMs && event.type !== "run") await sleep(options.paceMs, options.signal);
      yield event;
      if (event.type === "done" || event.type === "error") finished = true;
    }
  } catch (error) {
    if (isAbort(error) || options.signal.aborted) throw error;
    throw new DroppedStreamError();
  }
  if (!finished) throw new DroppedStreamError();
}
