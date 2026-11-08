import { expect, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";

test.use({ viewport: { width: 1280, height: 520 } });

test("the sidebar stays put while the page scrolls, and collapses to icons and back", async ({ page }) => {
  await signIn(page);
  await page.goto("/settings");
  const sidebar = page.getByRole("complementary", { name: "Sidebar" });
  const nav = sidebar.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Settings" })).toBeVisible();

  // Only the page moves, in its own scroll area: the window and the sidebar stay where they were.
  const before = await sidebar.boundingBox();
  const scroller = page.locator("#page-scroller");
  await page.mouse.move(800, 300);
  await page.mouse.wheel(0, 2000);
  await expect.poll(() => scroller.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  const after = await sidebar.boundingBox();
  expect(after?.y).toBe(before?.y);
  await expect(nav.getByRole("link", { name: "Today" })).toBeInViewport();
  // The page's bar: shown while scrolling, its thumb solid (WCAG 1.4.11), never a native bar beside it.
  const bar = page.locator("#page-scroller ~ [data-orientation=vertical]");
  await expect(bar).toBeVisible();
  const thumb = bar.locator(":scope > div");
  expect(await thumb.evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
  expect(await scroller.evaluate((el) => getComputedStyle(el).scrollbarWidth)).toBe("none");

  // Collapse: icons only, each link still named; remembered after a reload.
  const collapse = sidebar.getByRole("button", { name: "Collapse the sidebar" });
  await expect(collapse).toHaveAttribute("aria-expanded", "true");
  await collapse.click();
  const expand = sidebar.getByRole("button", { name: "Expand the sidebar" });
  await expect(expand).toHaveAttribute("aria-expanded", "false");
  await expect.poll(async () => (await sidebar.boundingBox())!.width).toBeLessThan(80);
  await expect(nav.getByRole("link", { name: "Applications" })).toBeVisible();
  await expect(sidebar.getByLabel("Working on")).toHaveCount(0);
  await expectAccessible(page, "sidebar collapsed");

  await page.reload();
  await expect(sidebar.getByRole("button", { name: "Expand the sidebar" })).toBeVisible();
  await sidebar.getByRole("button", { name: "Expand the sidebar" }).click();
  await expect.poll(async () => (await sidebar.boundingBox())!.width).toBeGreaterThan(200);
  await expect(sidebar.getByLabel("Working on")).toBeVisible();
});
