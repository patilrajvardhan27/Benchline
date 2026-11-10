import { expect, test } from "@playwright/test";
import { expectNoViolations, mockSnapshot } from "./support";

const ROUTES: [string, string][] = [
  ["/", "What should this drug cost?"],
  ["/items", "Items"],
  ["/items/ndc-00000000001", "ATORVASTATIN CALCIUM 20 MG TAB"],
  ["/opportunities", "Savings opportunities"],
  ["/anomalies", "Anomaly review"],
  ["/about", "About Benchline"],
  ["/terms", "Terms of Service"],
  ["/privacy", "Privacy Policy"],
  ["/legal", "Legal notice"],
  ["/accessibility", "Accessibility statement"],
  ["/contact", "Contact"],
  ["/this-page-does-not-exist", "Page not found"],
];

test.beforeEach(async ({ page }) => {
  await mockSnapshot(page);
  // Mid-animation frames have partial opacity, which makes contrast checks meaningless.
  // Reduced motion renders the final state; the motion tests below cover animation itself.
  await page.emulateMedia({ reducedMotion: "reduce" });
});

for (const [path, heading] of ROUTES) {
  test(`${path} has no WCAG 2.2 AA violations`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    // Wait for data-driven content to settle before scanning.
    await expect(page.locator("[aria-busy='true']")).toHaveCount(0);
    await expectNoViolations(page);
  });
}
