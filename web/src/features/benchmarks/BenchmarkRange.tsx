import type { CSSProperties } from "react";
import type { BenchmarkSnapshot } from "../../shared/api/types";
import { formatDate, formatUnitPrice } from "../../shared/format/format";

interface Props {
  benchmark: BenchmarkSnapshot;
  /** The item's own latest price, drawn as a marker when given. */
  price?: string | null;
}

/** p10 to p90 as a horizontal bar: light band is p10 to p90, dark band is p25 to p75. */
export function BenchmarkRange({ benchmark, price }: Props) {
  const nums = {
    p10: Number(benchmark.p10), p25: Number(benchmark.p25), p50: Number(benchmark.p50),
    p75: Number(benchmark.p75), p90: Number(benchmark.p90),
  };
  const own = price ? Number(price) : null;
  const lows = own === null ? [nums.p10] : [nums.p10, own];
  const highs = own === null ? [nums.p90] : [nums.p90, own];
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const span = max - min || 1;
  const pad = span * 0.06;
  const lo = Math.max(min - pad, 0);
  const pct = (v: number) => ((v - lo) / (max + pad - lo)) * 100;

  const at = (v: number): CSSProperties => ({ left: `${pct(v)}%` });
  // Labels are centred on their value, except near an edge where they would be cut off.
  const label = (v: number, extra: CSSProperties = {}): CSSProperties => {
    const p = pct(v);
    const shift = p < 16 ? "0%" : p > 84 ? "-100%" : "-50%";
    return { left: `${p}%`, transform: `translateX(${shift})`, ...extra };
  };
  const width = (a: number, b: number): CSSProperties => ({ left: `${pct(a)}%`, width: `${pct(b) - pct(a)}%` });

  return (
    <div>
      <div className="range" role="img"
        aria-label={`Benchmark range for ${benchmark.groupName}: p10 ${formatUnitPrice(benchmark.p10)}, p25 ${formatUnitPrice(benchmark.p25)}, median ${formatUnitPrice(benchmark.p50)}, p75 ${formatUnitPrice(benchmark.p75)}, p90 ${formatUnitPrice(benchmark.p90)}${own === null ? "" : `. This item: ${formatUnitPrice(price)}`}`}>
        <div className="range__track" />
        <div className="range__band" style={width(nums.p10, nums.p90)} />
        <div className="range__band range__band--core" style={width(nums.p25, nums.p75)} />
        <div className="range__tick" style={at(nums.p50)} />
        {own !== null && <div className="range__marker" style={at(own)} />}
        <span className="range__label" style={label(nums.p10)}>p10 {formatUnitPrice(benchmark.p10)}</span>
        <span className="range__label" style={label(nums.p50, { top: "-1.1rem" })}>median {formatUnitPrice(benchmark.p50)}</span>
        <span className="range__label" style={label(nums.p90)}>p90 {formatUnitPrice(benchmark.p90)}</span>
      </div>
      <p className="muted">
        Based on {benchmark.nObs} products in this group, week of {formatDate(benchmark.asOfWeek)}.
        {own !== null && " The orange line is this item's latest price."}
      </p>
    </div>
  );
}
