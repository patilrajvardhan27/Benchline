import { formatChange, formatDate, formatInt, formatMoney, formatUnitPrice } from "./format";

describe("formatUnitPrice", () => {
  it("keeps up to five places and at least two", () => {
    expect(formatUnitPrice("0.03121")).toBe("$0.03121");
    expect(formatUnitPrice("1.50000")).toBe("$1.50");
    expect(formatUnitPrice("2")).toBe("$2.00");
    expect(formatUnitPrice("1234.5")).toBe("$1,234.50");
  });
  it("shows n/a for a missing price", () => {
    expect(formatUnitPrice(null)).toBe("n/a");
    expect(formatUnitPrice(undefined)).toBe("n/a");
  });
});

describe("formatDate", () => {
  it("does not shift across time zones", () => {
    expect(formatDate("2026-10-29")).toBe("Oct 29, 2026");
    expect(formatDate("2026-01-01T00:00:00Z")).toBe("Jan 1, 2026");
  });
  it("handles bad input", () => {
    expect(formatDate("nope")).toBe("n/a");
    expect(formatDate(null)).toBe("n/a");
  });
});

describe("formatChange", () => {
  it("signs and rounds", () => {
    expect(formatChange("1.5", "1")).toBe("+50.0%");
    expect(formatChange("0.5", "1")).toBe("-50.0%");
    expect(formatChange("1", "1")).toBe("0.0%");
  });
  it("copes with no previous price", () => {
    expect(formatChange("1", null)).toBe("n/a");
    expect(formatChange("1", "0")).toBe("n/a");
  });
});

it("formats money and integers", () => {
  expect(formatMoney("125.5")).toBe("$125.50");
  expect(formatInt(1234567)).toBe("1,234,567");
});
