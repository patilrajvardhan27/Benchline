const dateFormat = new Intl.DateTimeFormat("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
const intFormat = new Intl.NumberFormat("en-US");

/** Unit prices keep up to five places, trimmed to at least two: "0.03121", "1.50". */
export function formatUnitPrice(value: string | null | undefined): string {
  if (value === null || value === undefined) return "n/a";
  const [whole = "0", fraction = ""] = value.split(".");
  const trimmed = fraction.replace(/0+$/, "").padEnd(2, "0");
  return `$${intFormat.format(Number(whole))}.${trimmed}`;
}

/** Totals are shown in whole cents. */
export function formatMoney(value: string): string {
  const number = Number(value);
  return number.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function formatInt(value: number): string {
  return intFormat.format(value);
}

/** "2026-10-29" shown as "Oct 29, 2026". Date-only strings are read as UTC. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "n/a";
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? "n/a" : dateFormat.format(date);
}

/** Percent change from previous to current, e.g. "+12.4%". */
export function formatChange(current: string, previous: string | null | undefined): string {
  if (!previous) return "n/a";
  const from = Number(previous);
  if (from === 0) return "n/a";
  const pct = ((Number(current) - from) / from) * 100;
  return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}
