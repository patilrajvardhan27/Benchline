import { act, renderHook } from "@testing-library/react";
import { useCountUp } from "./useCountUp";
import { useDebounce } from "./useDebounce";

function setReducedMotion(reduce: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({ matches: reduce, media: query, addEventListener: () => undefined, removeEventListener: () => undefined }),
  });
}

afterEach(() => { vi.useRealTimers(); setReducedMotion(false); });

describe("useDebounce", () => {
  it("waits for the value to settle", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ v }) => useDebounce(v, 200), { initialProps: { v: "a" } });
    rerender({ v: "ab" });
    rerender({ v: "abc" });
    expect(result.current).toBe("a");
    act(() => { vi.advanceTimersByTime(200); });
    expect(result.current).toBe("abc");
  });
});

describe("useCountUp", () => {
  it("returns the final value immediately when motion is reduced", () => {
    setReducedMotion(true);
    const { result } = renderHook(() => useCountUp(1234));
    expect(result.current).toBe(1234);
  });

  it("starts at zero and ends at the target when motion is allowed", async () => {
    setReducedMotion(false);
    const { result } = renderHook(() => useCountUp(500, 30));
    expect(result.current).toBe(0);
    await vi.waitFor(() => { expect(result.current).toBe(500); });
  });
});
