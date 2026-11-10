import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { DataTable } from "./DataTable";
import { LineChart } from "./LineChart";
import { Pagination } from "./Pagination";
import { Skeleton } from "./Skeleton";
import { StatStrip } from "./StatStrip";
import { BenchmarkRange } from "../../features/benchmarks/BenchmarkRange";

describe("DataTable", () => {
  const rows = [{ id: "1", name: "Aspirin" }, { id: "2", name: "Zinc" }];
  const columns = [{ key: "n", header: "Name", render: (r: (typeof rows)[number]) => r.name }];

  it("renders a captioned table with column headers", async () => {
    const { container } = render(<DataTable caption="Drugs" columns={columns} rows={rows} getRowKey={(r) => r.id} />);
    expect(screen.getByRole("table", { name: "Drugs" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Pagination", () => {
  const meta = { page: 1, size: 10, totalElements: 35, totalPages: 4 };

  it("reports the range and moves between pages", async () => {
    const onChange = vi.fn();
    render(<Pagination page={meta} onChange={onChange} />);
    expect(screen.getByText("11 to 20 of 35")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(onChange).toHaveBeenNthCalledWith(1, 2);
    expect(onChange).toHaveBeenNthCalledWith(2, 0);
  });

  it("disables the ends and hides itself for a single page", () => {
    const { rerender } = render(<Pagination page={{ ...meta, page: 0 }} onChange={() => undefined} />);
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    rerender(<Pagination page={{ ...meta, page: 3 }} onChange={() => undefined} />);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    rerender(<Pagination page={{ page: 0, size: 10, totalElements: 5, totalPages: 1 }} onChange={() => undefined} />);
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
});

describe("StatStrip and Skeleton", () => {
  it("shows skeletons while loading and values after", async () => {
    const { container, rerender } = render(<StatStrip loading stats={[{ label: "Items", value: "5" }]} />);
    expect(container.querySelector(".skeleton")).toBeInTheDocument();
    expect(container.querySelector("dl")).toHaveAttribute("aria-busy", "true");
    rerender(<StatStrip stats={[{ label: "Items", value: "5" }]} />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("hides skeletons from assistive technology", () => {
    const { container } = render(<Skeleton variant="row" count={3} />);
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(3);
  });
});

describe("charts", () => {
  it("LineChart is an image with a text label and passes axe", async () => {
    const { container } = render(
      <LineChart ariaLabel="Price from Jan to Mar" formatY={(v) => `$${v.toFixed(2)}`}
        band={{ low: 1, high: 2, label: "p25 to p75" }}
        series={[{ id: "a", step: true, points: [
          { date: "2026-01-01", value: 1 }, { date: "2026-02-01", value: 2, flagged: true }, { date: "2026-03-01", value: 1.5 }] }]} />,
    );
    expect(screen.getByRole("img", { name: "Price from Jan to Mar" })).toBeInTheDocument();
    expect(container.querySelectorAll(".point--flag")).toHaveLength(1);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("LineChart renders nothing without data", () => {
    const { container } = render(<LineChart series={[]} ariaLabel="x" formatY={String} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("BenchmarkRange describes every percentile in words", async () => {
    const { container } = render(
      <BenchmarkRange price="0.05" benchmark={{ groupId: "g", groupName: "TEST 10 MG", asOfWeek: "2026-10-26",
        p10: "0.02", p25: "0.025", p50: "0.03", p75: "0.035", p90: "0.04", nObs: 9, method: "m" }} />,
    );
    const label = screen.getByRole("img").getAttribute("aria-label") ?? "";
    expect(label).toContain("median $0.03");
    expect(label).toContain("This item: $0.05");
    expect(await axe(container)).toHaveNoViolations();
  });
});
