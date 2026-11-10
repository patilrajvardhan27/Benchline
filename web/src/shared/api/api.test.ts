import { stubSnapshotFetch } from "../../test/snapshot";
import { demoGet } from "./demo";
import { ApiError, messageForStatus } from "./errors";
import { toQueryString } from "./query";
import type { Item, ItemPage } from "./types";
import { shouldRetry } from "../../app/queryClient";

describe("toQueryString", () => {
  it("skips empty values", () => {
    expect(toQueryString({ a: 1, b: "", c: undefined, d: "x y" })).toBe("?a=1&d=x+y");
    expect(toQueryString()).toBe("");
  });
});

describe("messageForStatus", () => {
  it("never repeats server text", () => {
    expect(messageForStatus(404)).toMatch(/could not find/);
    expect(messageForStatus(500)).toMatch(/try again/);
    expect(messageForStatus(418)).toBe("The request could not be completed.");
  });
});

describe("shouldRetry", () => {
  it("retries network and server failures only, twice", () => {
    expect(shouldRetry(0, new ApiError(503, "x"))).toBe(true);
    expect(shouldRetry(0, new ApiError(0, "x"))).toBe(true);
    expect(shouldRetry(0, new ApiError(404, "x"))).toBe(false);
    expect(shouldRetry(2, new ApiError(503, "x"))).toBe(false);
    expect(shouldRetry(0, new Error("boom"))).toBe(false);
  });
});

describe("demo router", () => {
  beforeEach(() => { stubSnapshotFetch(); });

  it("searches by description and by NDC prefix", async () => {
    const byName = await demoGet<ItemPage>("/api/v1/items", { query: "metformin" });
    expect(byName.content.map((i) => i.id)).toEqual(["ndc-00000000003"]);
    const byNdc = await demoGet<ItemPage>("/api/v1/items", { query: "00000000001" });
    expect(byNdc.content).toHaveLength(1);
  });

  it("paginates", async () => {
    const page = await demoGet<ItemPage>("/api/v1/items", { page: 1, size: 2 });
    expect(page.content).toHaveLength(1);
    expect(page.page).toMatchObject({ page: 1, size: 2, totalElements: 3, totalPages: 2 });
  });

  it("clamps absurd page sizes", async () => {
    const page = await demoGet<ItemPage>("/api/v1/items", { size: 9999 });
    expect(page.page.size).toBe(100);
  });

  it("returns one item and rejects an unknown one with a 404", async () => {
    expect((await demoGet<Item>("/api/v1/items/ndc-00000000001")).ndc11).toBe("00000000001");
    await expect(demoGet("/api/v1/items/ndc-99999999999")).rejects.toMatchObject({ status: 404 });
  });

  it("serves history, equivalents, benchmarks and opportunities", async () => {
    expect(await demoGet<unknown[]>("/api/v1/items/ndc-00000000001/prices")).toHaveLength(2);
    expect(await demoGet<unknown[]>("/api/v1/items/ndc-00000000001/equivalents")).toHaveLength(1);
    expect(await demoGet<{ p50: string }>("/api/v1/benchmarks/groups/grp-atorvastatin")).toMatchObject({ p50: "0.03" });
    const report = await demoGet<{ lines: unknown[]; totalSavings: string }>("/api/v1/members/fac-1/opportunities");
    expect(report.lines).toHaveLength(1);
  });

  it("filters anomalies by status", async () => {
    expect((await demoGet<{ content: unknown[] }>("/api/v1/anomalies", { status: "OPEN" })).content).toHaveLength(1);
    expect((await demoGet<{ content: unknown[] }>("/api/v1/anomalies", { status: "DISMISSED" })).content).toHaveLength(0);
  });

  it("answers an unknown route with a 404", async () => {
    await expect(demoGet("/api/v1/nope")).rejects.toBeInstanceOf(ApiError);
  });
});
