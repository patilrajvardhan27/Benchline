import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import { FILES } from "../src/test/fixtures";

/** Serves the demo snapshot from fixtures so tests do not depend on exported data. */
export async function mockSnapshot(page: Page) {
  await page.route("**/demo/**", async (route) => {
    const file = new URL(route.request().url()).pathname.replace("/demo/", "");
    const body = FILES[file];
    if (body === undefined) return route.fulfill({ status: 404, body: "{}" });
    return route.fulfill({ json: body });
  });
}

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/** Fails on any WCAG 2.2 AA violation, with enough detail to fix it. */
export async function expectNoViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const summary = results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)\n  ${v.nodes.map((n) => n.target.join(" ")).join("\n  ")}`);
  expect(summary, summary.join("\n")).toEqual([]);
}
