import { useRef } from "react";
import { formatDate } from "../format/format";
import { useElementWidth } from "../hooks/useElementWidth";
import { linearScale, linePath, niceTicks, stepPath } from "./chartMath";

export interface ChartPoint {
  date: string; // YYYY-MM-DD
  value: number;
  flagged?: boolean;
}

export interface ChartSeries {
  id: string;
  points: ChartPoint[];
  step?: boolean;
  dashed?: boolean;
}

interface Props {
  series: ChartSeries[];
  ariaLabel: string;
  band?: { low: number; high: number; label: string };
  formatY: (value: number) => string;
}

const MIN_WIDTH = 280;
const NARROW = 480;

const toTime = (date: string) => Date.parse(`${date}T00:00:00Z`);

/** Dependency-free SVG line chart. Pair it with a data table for screen reader users. */
export function LineChart({ series, ariaLabel, band, formatY }: Props) {
  const svg = useRef<SVGSVGElement>(null);
  const measured = useElementWidth(svg);
  // Drawn at its real pixel width, so labels keep their size on a phone.
  const W = Math.max(measured, MIN_WIDTH);
  const H = Math.round(Math.min(Math.max(W * 0.42, 200), 300));
  const M = { top: 12, right: 12, bottom: 28, left: W < NARROW ? 50 : 64 };

  const all = series.flatMap((s) => s.points);
  if (all.length === 0) return null;

  const times = all.map((p) => toTime(p.date));
  const values = all.map((p) => p.value);
  if (band) values.push(band.low, band.high);
  const xMin = Math.min(...times);
  const xMax = Math.max(...times);
  const pad = (Math.max(...values) - Math.min(...values)) * 0.08 || Math.max(...values) * 0.1 || 1;
  const yMin = Math.max(Math.min(...values) - pad, 0);
  const yMax = Math.max(...values) + pad;

  const x = linearScale([xMin, xMax === xMin ? xMin + 1 : xMax], [M.left, W - M.right]);
  const y = linearScale([yMin, yMax], [H - M.bottom, M.top]);
  const ticks = niceTicks(yMin, yMax);
  const xLabels = [xMin, xMin + (xMax - xMin) / 2, xMax].map((t) => new Date(t).toISOString().slice(0, 10));

  return (
    <svg ref={svg} className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}>
      {band && (
        <g>
          <rect className="band" x={M.left} width={W - M.left - M.right}
            y={y(band.high)} height={Math.max(y(band.low) - y(band.high), 1)} />
          <text x={W - M.right - 4} y={y(band.low) - 6} textAnchor="end">{band.label}</text>
        </g>
      )}
      {ticks.map((t) => (
        <g key={t}>
          <line className="axis" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
          <text x={M.left - 8} y={y(t) + 4} textAnchor="end">{formatY(t)}</text>
        </g>
      ))}
      {xLabels.map((d, i) => (
        <text key={`${d}-${i}`} x={x(toTime(d))} y={H - 8}
          textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}>
          {formatDate(d)}
        </text>
      ))}
      {series.map((s) => {
        const pts = s.points.map((p) => ({ x: x(toTime(p.date)), y: y(p.value) }));
        const d = s.step ? stepPath(pts, W - M.right) : linePath(pts);
        return (
          <g key={s.id}>
            <path className={s.dashed ? "line line--alt" : "line"} d={d} pathLength={s.dashed ? undefined : 1} />
            {s.points.map((p, i) => {
              const pt = pts[i];
              if (!pt || (!p.flagged && s.points.length > 40)) return null;
              return <circle key={`${p.date}-${i}`} className={p.flagged ? "point point--flag" : "point"}
                cx={pt.x} cy={pt.y} r={p.flagged ? 6 : 2.5} />;
            })}
          </g>
        );
      })}
    </svg>
  );
}
