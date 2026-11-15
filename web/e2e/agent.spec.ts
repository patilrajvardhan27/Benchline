import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import { expectNoViolations, mockSnapshot } from "./support";

// Recorded from the agent's own stream encoder (ml-service: python -m app.agent.record).
// No API key, no model, no backend: CI replays exactly what the server sends.
const DIR = join(process.cwd(), "public", "demo", "agent");
const RECORDING = readFileSync(join(DIR, "fair-price-sertraline.sse"), "utf8");
const INDEX = readFileSync(join(DIR, "index.json"), "utf8");
const QUESTION = "Is $0.06 per tablet a fair price for sertraline 50 mg?";
const DROPPED = RECORDING.slice(0, RECORDING.indexOf("event: thinking", RECORDING.indexOf("event: tool_result")));

/** Serves the recording; each entry in `bodies` answers one run, the last one repeats. */
async function serveRecording(page: Page, ...bodies: string[]) {
  let run = 0;
  await page.route("**/demo/agent/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("index.json")) return route.fulfill({ body: INDEX, contentType: "application/json" });
    const body = bodies[Math.min(run++, bodies.length - 1)] ?? RECORDING;
    return route.fulfill({ body, contentType: "text/event-stream" });
  });
}

async function ask(page: Page) {
  await page.goto("/ask");
  await page.getByRole("button", { name: QUESTION }).click();
}

const answer = (page: Page) => page.getByRole("region", { name: "Answer" });

test.beforeEach(async ({ page }) => {
  await mockSnapshot(page);
});

test("streams each step, then the answer with sources that open the item page", async ({ page }) => {
  await serveRecording(page);
  await ask(page);

  const turn = page.locator(".agent-turn");
  await expect(turn).toHaveAttribute("aria-busy", "true");
  await expect(turn.getByText("I'll check the benchmark for sertraline 50 mg")).toBeVisible();
  await expect(turn.locator(".skeleton").first()).toBeVisible();
  await expect(turn.getByText("Benchmark for sertraline 50 mg")).toBeVisible();
  await expect(page.getByRole("status")).toContainText(/Looking up|Found|Thinking/);

  await expect(answer(page)).toContainText("above the p90", { timeout: 15_000 });
  await expect(turn).toHaveAttribute("aria-busy", "false");
  await expect(page.getByRole("status")).toHaveText("Answer ready.");
  await expect(turn.getByText("Recorded run")).toBeVisible();
  await expect(turn.locator(".skeleton")).toHaveCount(0);

  await answer(page).getByRole("link", { name: /NDC 16729021615/ }).click();
  await expect(page).toHaveURL(/\/items\/ndc-16729021615$/);
});

test("each tool call opens to show its arguments and sources", async ({ page }) => {
  await serveRecording(page);
  await ask(page);
  await expect(answer(page)).toBeVisible({ timeout: 15_000 });

  const step = page.locator(".agent-step--tool").filter({ hasText: "Equivalent products for sertraline 50 mg" });
  await expect(step.locator("pre")).toBeHidden();
  await step.locator("summary").click();
  await expect(step.locator("pre")).toContainText('"drug": "sertraline 50 mg"');
  await expect(step.getByRole("link")).toHaveCount(5);
});

test("cancel stops the run, retry runs it again", async ({ page }) => {
  await serveRecording(page);
  await ask(page);
  await expect(page.getByText("Benchmark for sertraline 50 mg")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();

  await expect(page.getByText("You cancelled this question.")).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("Question cancelled.");
  await expect(answer(page)).toHaveCount(0);

  await page.getByRole("button", { name: "Retry" }).click();
  await expect(answer(page)).toContainText("above the p90", { timeout: 15_000 });
});

test("a dropped stream is reported and can be retried", async ({ page }) => {
  await serveRecording(page, DROPPED, RECORDING);
  await ask(page);

  await expect(page.getByText("The connection dropped before the answer finished.")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("status")).toHaveText("The connection dropped. You can retry.");
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(answer(page)).toContainText("above the p90", { timeout: 15_000 });
  await expect(page.locator(".agent-turn")).toHaveCount(1);
});

test("keyboard only: a suggestion runs from the keyboard and focus is never lost", async ({ page }) => {
  await serveRecording(page);
  await page.goto("/ask");
  await page.getByLabel("Your question").fill(QUESTION);
  await page.keyboard.press("Enter");
  await expect(answer(page)).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(":focus")).toHaveCount(1);
});

test("no WCAG 2.2 AA violations, idle and after an answer", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await serveRecording(page);
  await page.goto("/ask");
  await expect(page.getByRole("heading", { level: 1, name: "Ask Benchline" })).toBeVisible();
  await expectNoViolations(page);

  await page.getByRole("button", { name: QUESTION }).click();
  await expect(answer(page)).toBeVisible({ timeout: 15_000 });
  await page.locator(".agent-step--tool summary").first().click();
  await expectNoViolations(page);
});
