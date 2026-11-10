import { vi } from "vitest";
import { FILES } from "./fixtures";

export { FILES, ITEM } from "./fixtures";

/** Serves the fixtures above as if they were the /demo snapshot files. */
export function stubSnapshotFetch() {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const file = url.replace("/demo/", "");
    const body = FILES[file];
    return Promise.resolve(body === undefined
      ? new Response("{}", { status: 404 })
      : new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
