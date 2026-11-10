import { type SyntheticEvent, useId, useState } from "react";
import { useNavigate } from "react-router-dom";
import { OverviewStats } from "../features/overview/OverviewStats";
import { PipelineFlow } from "../features/overview/PipelineFlow";
import { PageShell } from "../shared/ui/PageShell";

export function OverviewPage() {
  const [text, setText] = useState("");
  const navigate = useNavigate();
  const id = useId();

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    void navigate(text.trim() ? `/items?q=${encodeURIComponent(text.trim())}` : "/items");
  };

  return (
    <PageShell title="What should this drug cost?"
      description="Weekly CMS acquisition costs, grouped by product and benchmarked as price changes arrive.">
      <div className="stack">
        <form onSubmit={submit} className="reveal" style={{ "--i": 0 } as React.CSSProperties} role="search">
          <div className="field">
            <label htmlFor={id}>Look up a product</label>
            <div className="cluster">
              <input id={id} type="search" value={text} placeholder="metformin 500 mg" autoComplete="off"
                onChange={(e) => { setText(e.target.value); }} />
              <button type="submit" className="btn">Search</button>
            </div>
          </div>
        </form>
        <div className="reveal" style={{ "--i": 1 } as React.CSSProperties}><OverviewStats /></div>
        <section className="panel reveal" style={{ "--i": 2 } as React.CSSProperties} aria-labelledby="flow-h">
          <h2 id="flow-h">How a price change becomes a benchmark</h2>
          <PipelineFlow />
        </section>
        <section className="prose reveal" style={{ "--i": 3 } as React.CSSProperties} aria-labelledby="scope-h">
          <h2 id="scope-h">What these numbers are</h2>
          <p>
            NADAC is the average price retail pharmacies pay to acquire a drug, surveyed by CMS and
            published weekly. It is a market reference, not the contract price any one hospital pays.
            Benchline groups products that share a description and reports the spread across them.
          </p>
        </section>
      </div>
    </PageShell>
  );
}
