import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { renderWithProviders } from "../../test/render";
import { AgentPanel, SUGGESTIONS } from "./AgentPanel";
import type { AgentRunner } from "./client";
import type { AgentEvent } from "./events";
import { useAgentStore } from "./store";

const CITE = { item_id: "ndc-00000000001", label: "ATORVASTATIN 20 MG TAB (NDC 00000000001)" };

function gated(events: AgentEvent[]) {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((r) => { release = r; });
  const run: AgentRunner = async function* () {
    yield* events.slice(0, 2);
    await gate;              // holds the run mid-tool so the pending state can be checked
    yield* events.slice(2);
  };
  return { run, release };
}

const EVENTS: AgentEvent[] = [
  { type: "thinking", data: { text: "Checking the benchmark." } },
  { type: "tool_call", data: { call_id: "c1", name: "get_benchmark", arguments: '{"drug":"atorvastatin"}', label: "Benchmark for atorvastatin" } },
  { type: "tool_result", data: { call_id: "c1", name: "get_benchmark", ok: true, summary: "median $0.03", citations: [CITE] } },
  { type: "answer", data: { text: "That price is fair.", citations: [CITE] } },
  { type: "done", data: { steps: 2, tokens: 10, cost_usd: 0 } },
];

beforeEach(() => useAgentStore.getState().clear());

it("shows each step live, then the answer with linked sources", async () => {
  const { run, release } = gated(EVENTS);
  const { container } = renderWithProviders(<AgentPanel run={run} />);
  await userEvent.click(screen.getByRole("button", { name: SUGGESTIONS[0] }));

  const turn = await screen.findByRole("listitem", { name: "" , busy: true });
  expect(within(turn).getByText("Checking the benchmark.")).toBeInTheDocument();
  expect(within(turn).getByText("Benchmark for atorvastatin")).toBeInTheDocument();
  expect(container.querySelector(".agent-step--running .skeleton")).not.toBeNull();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("Looking up: Benchmark for atorvastatin");

  release();
  expect(await screen.findByText("That price is fair.")).toBeInTheDocument();
  const answer = screen.getByRole("region", { name: "Answer" });
  expect(within(answer).getByRole("link", { name: CITE.label })).toHaveAttribute("href", "/items/ndc-00000000001");
  expect(screen.getByRole("status")).toHaveTextContent("Answer ready.");
  expect(screen.getByText(/2 steps, 1 lookup\./)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();
});

it("tool details open to show the arguments", async () => {
  const { run, release } = gated(EVENTS);
  release();
  renderWithProviders(<AgentPanel run={run} />);
  await userEvent.click(screen.getByRole("button", { name: SUGGESTIONS[0] }));
  await screen.findByText("That price is fair.");

  await userEvent.click(screen.getByText("Benchmark for atorvastatin"));
  expect(screen.getByText(/"drug": "atorvastatin"/)).toBeVisible();
});

it("cancel ends the run and offers a retry", async () => {
  const { run } = gated(EVENTS);
  renderWithProviders(<AgentPanel run={run} />);
  await userEvent.click(screen.getByRole("button", { name: SUGGESTIONS[0] }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));

  expect(await screen.findByText("You cancelled this question.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Question cancelled."));
});

it("typed questions go through the same path", async () => {
  const { run, release } = gated(EVENTS);
  release();
  renderWithProviders(<AgentPanel run={run} />);
  const ask = screen.getByRole("button", { name: "Ask" });
  expect(ask).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Your question"), "Is atorvastatin 20 mg fair at 0.05?");
  await userEvent.click(ask);
  expect(await screen.findByRole("heading", { level: 2, name: "Is atorvastatin 20 mg fair at 0.05?" })).toBeInTheDocument();
});
