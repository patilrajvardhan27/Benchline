import { ApiError } from "./errors";
import type {
  Anomaly,
  AnomalyPage,
  BenchmarkHistory,
  BenchmarkSnapshot,
  Equivalent,
  Facility,
  Item,
  ItemPage,
  Opportunity,
  PricePoint,
} from "./types";
import type { QueryParams } from "./query";

/**
 * Demo mode serves a static snapshot exported from a real run (see
 * scripts/export_demo_snapshot.py), so the site works on free static hosting
 * with no backend. Only the shapes the real API returns are produced here.
 */
const BASE = "/demo";
const DEFAULT_SIZE = 25;

async function load<T>(file: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${BASE}/${file}`, { signal });
  if (!response.ok) throw new ApiError(404, "We could not find what you asked for.");
  return (await response.json()) as T;
}

function paging(query?: QueryParams): { page: number; size: number } {
  const page = Math.max(Number(query?.page ?? 0) || 0, 0);
  const size = Math.min(Math.max(Number(query?.size ?? DEFAULT_SIZE) || DEFAULT_SIZE, 1), 100);
  return { page, size };
}

function paginate<T>(rows: T[], query?: QueryParams) {
  const { page, size } = paging(query);
  return {
    content: rows.slice(page * size, page * size + size),
    page: { page, size, totalElements: rows.length, totalPages: Math.ceil(rows.length / size) },
  };
}

interface ItemFile { prices: PricePoint[]; equivalents: Equivalent[] }
interface OpportunityFile { facility: Facility; lines: Opportunity[]; totalSavings: string }

export async function demoGet<T>(path: string, query?: QueryParams, signal?: AbortSignal): Promise<T> {
  const result = await route(path, query, signal);
  return result as T;
}

async function route(path: string, query: QueryParams | undefined, signal?: AbortSignal): Promise<unknown> {
  const parts = path.replace(/^\/api\/v1\//, "").split("/");
  const [head, id, tail] = parts;

  if (head === "overview" || head === "config") return load(`${head}.json`, signal);

  if (head === "items" && !id) {
    const all = await load<Item[]>("items.json", signal);
    const text = String(query?.query ?? "").trim().toLowerCase();
    const group = query?.group;
    const rows = all.filter(
      (i) =>
        (!text || i.description.toLowerCase().includes(text) || i.ndc11.startsWith(text)) &&
        (!group || i.groupId === group),
    );
    return paginate(rows, query) satisfies ItemPage;
  }
  if (head === "items" && id) {
    const items = await load<Item[]>("items.json", signal);
    const item = items.find((i) => i.id === id);
    if (!item) throw new ApiError(404, "We could not find what you asked for.");
    if (!tail) return item;
    const file = await load<ItemFile>(`items/${id}.json`, signal);
    return tail === "prices" ? file.prices : file.equivalents;
  }
  if (head === "benchmarks" && id === "groups" && parts[2]) {
    const file = await load<{ latest: BenchmarkSnapshot; history: BenchmarkHistory }>(
      `benchmarks/${parts[2]}.json`, signal);
    return parts[3] === "history" ? file.history : file.latest;
  }
  if (head === "members" && !id) return load<Facility[]>("members.json", signal);
  if (head === "members" && id) {
    const file = await load<OpportunityFile>(`opportunities/${id}.json`, signal);
    const { content, page } = paginate(file.lines, query);
    return { facility: file.facility, totalSavings: file.totalSavings, lines: content, page };
  }
  if (head === "anomalies") {
    const all = await load<Anomaly[]>("anomalies.json", signal);
    const status = query?.status;
    return paginate(all.filter((a) => !status || a.status === status), query) satisfies AnomalyPage;
  }
  throw new ApiError(404, "We could not find what you asked for.");
}
