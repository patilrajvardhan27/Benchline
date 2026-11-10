import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BenchmarkRange } from "../benchmarks/BenchmarkRange";
import { AnomalyTable } from "./AnomalyTable";
import type { Anomaly } from "../../shared/api/types";

const base: Anomaly = {
  id: "a1", pricePointId: "p1", groupId: "g", groupName: "OMEPRAZOLE DR 20 MG CAPSULE", itemId: "ndc-00000000001",
  unitPrice: "0.02945", previousUnitPrice: "0.02768", effectiveDate: "2026-09-23", score: 4.9,
  method: "robust-z/log-change", status: "OPEN", detectedAt: "2026-09-30T00:00:00Z",
};

describe("AnomalyTable", () => {
  it("tells apart products in one group that changed together by showing each NDC", () => {
    const rows = [base, { ...base, id: "a2", itemId: "ndc-00000000002" }];
    render(<MemoryRouter><AnomalyTable rows={rows} canReview={false} onReview={() => undefined} /></MemoryRouter>);
    expect(screen.getByText("NDC 00000000001")).toBeInTheDocument();
    expect(screen.getByText("NDC 00000000002")).toBeInTheDocument();
  });
});

describe("BenchmarkRange labels", () => {
  const benchmark = { groupId: "g", groupName: "TEST", asOfWeek: "2026-10-26", p10: "0.10", p25: "0.20",
    p50: "0.30", p75: "0.40", p90: "0.50", nObs: 9, method: "m" };

  it("keeps labels at the bar's ends inside the bar", () => {
    const { container } = render(<BenchmarkRange benchmark={benchmark} />);
    const transforms = [...container.querySelectorAll<HTMLElement>(".range__label")].map((l) => l.style.transform);
    expect(transforms).toContain("translateX(0%)");     // p10 hugs the left edge
    expect(transforms).toContain("translateX(-100%)");  // p90 hugs the right edge
    expect(transforms).toContain("translateX(-50%)");   // the median is centred
  });
});
