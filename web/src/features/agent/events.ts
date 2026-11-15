import { z } from "zod";
import type { SseMessage } from "./sse";

const citation = z.object({ item_id: z.string().regex(/^[\w-]+$/), label: z.string() });

const schemas = {
  run: z.object({ run_id: z.string() }),
  thinking: z.object({ text: z.string() }),
  tool_call: z.object({ call_id: z.string(), name: z.string(), arguments: z.string(), label: z.string() }),
  tool_result: z.object({
    call_id: z.string(), name: z.string(), ok: z.boolean(), summary: z.string(), citations: z.array(citation),
  }),
  answer: z.object({ text: z.string(), citations: z.array(citation) }),
  error: z.object({ message: z.string(), retryable: z.boolean() }),
  done: z.object({ steps: z.number(), tokens: z.number(), cost_usd: z.number() }),
};

type Schemas = typeof schemas;
export type AgentEvent = { [K in keyof Schemas]: { type: K; data: z.infer<Schemas[K]> } }[keyof Schemas];
export type Citation = z.infer<typeof citation>;

/** Checks each event against the contract; anything unknown or malformed is dropped, not trusted. */
export function toAgentEvent(message: SseMessage): AgentEvent | null {
  if (!(message.event in schemas)) return null;
  const type = message.event as keyof Schemas;
  try {
    const parsed = schemas[type].safeParse(JSON.parse(message.data));
    return parsed.success ? ({ type, data: parsed.data } as AgentEvent) : null;
  } catch {
    return null;
  }
}
