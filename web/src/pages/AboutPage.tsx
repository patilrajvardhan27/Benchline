import { Link } from "react-router-dom";
import { PageShell } from "../shared/ui/PageShell";

export function AboutPage() {
  return (
    <PageShell title="About Benchline" description="An event-driven price benchmarking service built on public data.">
      <div className="prose stack">
        <section>
          <h2>What it does</h2>
          <p>
            Benchline takes weekly drug acquisition costs published by CMS, groups products that share a
            description, and keeps a percentile benchmark (p10, p25, p50, p75, p90) for each group. It
            flags price moves that are unusual for their group and shows where a purchase sits against
            the benchmark.
          </p>
        </section>
        <section>
          <h2>How the benchmark is calculated</h2>
          <ol>
            <li>Raw NADAC files are saved unchanged, then cleaned. Rows with bad NDCs, prices, units or dates are rejected and counted.</li>
            <li>CMS republishes every rate each week, so only the first publication of each rate is kept. What remains is a stream of price changes.</li>
            <li>Changes are sent in date order through the API, which stores each one and queues an event in the same database transaction.</li>
            <li>A worker reads the event and recomputes the group's percentiles from each product's latest rate within 52 weeks. Replaying an event cannot count it twice.</li>
          </ol>
        </section>
        <section>
          <h2>What the anomaly score means</h2>
          <p>
            Each price change is compared with the usual changes for its group using a robust z-score (median
            and median absolute deviation, so a few extreme moves do not hide others). A change is flagged
            when that score is at least 3.5 and it also falls outside the interquartile fence. Flags are
            suggestions for a person to review, not findings.
          </p>
        </section>
        <section>
          <h2>Limits you should know</h2>
          <ul>
            <li>NADAC is what retail pharmacies pay on average. It is not a hospital contract price.</li>
            <li>Groups are made from matching descriptions. They are not checked for therapeutic equivalence.</li>
            <li>Facilities and purchase lines are synthetic and labelled that way wherever they appear.</li>
          </ul>
        </section>
        <section>
          <h2>More</h2>
          <p>
            Read the <Link to="/legal">Legal notice</Link> for data licenses, or the{" "}
            <Link to="/accessibility">Accessibility statement</Link>.
          </p>
        </section>
      </div>
    </PageShell>
  );
}
