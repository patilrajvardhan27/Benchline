import { expect, test } from "@playwright/test";
import { mockSnapshot } from "./support";

test.beforeEach(async ({ page }) => { await mockSnapshot(page); });

test("search for a product and open its detail page", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Look up a product").fill("metformin");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/\/items\?q=metformin/);
  await page.getByRole("link", { name: /METFORMIN/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: /METFORMIN/ })).toBeVisible();
});

test("item detail shows price chart, benchmark range and equivalents", async ({ page }) => {
  await page.goto("/items/ndc-00000000001");
  await expect(page.getByRole("img", { name: /NADAC price per unit/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /Benchmark range/ })).toBeVisible();
  await expect(page.getByRole("table", { name: /Lower-priced products/ })).toBeVisible();
  await page.getByText("View the same data as a table").click();
  await expect(page.getByRole("table", { name: "Price changes, newest first" })).toBeVisible();
});

test("keyboard users can skip to the content", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible(); // app has rendered
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to main content" });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});

test("navigating moves focus to the new page heading", async ({ page }) => {
  await page.goto("/");
  // Wait for the real first page; the very first page of a visit is not given focus on purpose.
  await expect(page.getByRole("heading", { level: 1, name: "What should this drug cost?" })).toBeVisible();
  await page.getByRole("link", { name: "About", exact: true }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "About Benchline" })).toBeFocused();
});

test("footer exposes the legal pages", async ({ page }) => {
  await page.goto("/");
  const legal = page.getByRole("navigation", { name: "Legal and help" });
  for (const name of ["Terms of Service", "Privacy Policy", "Legal notice", "Accessibility", "Contact"]) {
    await expect(legal.getByRole("link", { name })).toBeVisible();
  }
  await expect(page.getByText("Not affiliated with or endorsed by Vizient, Inc.")).toBeVisible();
});

test("contact form validates before composing an email", async ({ page }) => {
  await page.goto("/contact");
  await page.getByLabel("Your email").fill("nope");
  await page.getByLabel("Message").fill("too short");
  await page.getByRole("button", { name: /open in my email app/i }).click();
  await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  await expect(page.getByText("Write at least 10 characters.")).toBeVisible();
});

test("opportunities page always says the data is synthetic", async ({ page }) => {
  await page.goto("/opportunities");
  await expect(page.getByRole("note")).toContainText("Synthetic demo data");
  await expect(page.getByRole("table", { name: /Synthetic purchase lines/ })).toBeVisible();
});

test("unknown product shows a plain error, not internals", async ({ page }) => {
  await page.goto("/items/ndc-99999999999");
  const alert = page.getByRole("alert");
  await expect(alert).toContainText("We could not find what you asked for.");
  await expect(page.locator("body")).not.toContainText(/stack|exception|at Object/i);
});

test.describe("motion", () => {
  test("pages animate in by default", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("/about");
    const name = await page.locator(".page-enter").evaluate((el) => getComputedStyle(el).animationName);
    expect(name).toBe("bl-rise");
  });

  test("animations are off when the user asks for reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/about");
    const name = await page.locator(".page-enter").evaluate((el) => getComputedStyle(el).animationName);
    expect(name).toBe("none");
  });
});
