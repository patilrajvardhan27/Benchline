export interface SseMessage {
  id: string | null;
  event: string;
  data: string;
}

/** One SSE block to a message. Comment lines (": ...") and blocks without data are skipped. */
export function parseBlock(block: string): SseMessage | null {
  let id: string | null = null;
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? "" : line.slice(colon + 1).replace(/^ /, "");
    if (field === "id") id = value;
    else if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  return data.length ? { id, event, data: data.join("\n") } : null;
}

/**
 * Splits a response body into Server-Sent Events as bytes arrive. A network chunk can end anywhere,
 * mid-line or mid-character, so text is buffered until a blank line closes each event.
 */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<SseMessage> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      // A lone \r at the very end may be half of \r\n, so it waits for the next chunk.
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n|\r(?!$)/g, "\n");
      let end: number;
      while ((end = buffer.indexOf("\n\n")) >= 0) {
        const message = parseBlock(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        if (message) yield message;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
