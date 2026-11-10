import type { CSSProperties } from "react";

const STEPS = [
  { name: "Pipelines", note: "Clean CMS files, send changes week by week" },
  { name: "Pricing API", note: "Stores the price and its event together" },
  { name: "Kafka", note: "One ordered stream per product group" },
  { name: "Benchmark worker", note: "Recomputes p10 to p90, once per event" },
  { name: "PostgreSQL", note: "Holds prices, benchmarks and anomalies" },
  { name: "This dashboard", note: "Reads the result" },
];

/** Shows the path a price change takes. A small marker travels along each box. */
export function PipelineFlow() {
  return (
    <ol className="flow" aria-label="How a price change moves through Benchline">
      {STEPS.map((step, i) => (
        <li key={step.name} style={{ "--i": i } as CSSProperties}>
          <strong>{i + 1}. {step.name}</strong>
          <span>{step.note}</span>
        </li>
      ))}
    </ol>
  );
}
