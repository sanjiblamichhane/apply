import { expect, test } from "@playwright/test";

import { expectAccessible, posting, signIn } from "./helpers";

const SCREENS = ["/today", "/ready", "/needs-you", "/matches", "/searches", "/searches/new", "/sources", "/sources/new", "/applications",
  "/applications?view=list", "/profiles", "/profiles/new", "/answers", "/settings"];

for (const scheme of ["light", "dark"] as const) {
  test(`every screen passes axe (WCAG 2.2 AA) in ${scheme}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await signIn(page);
    for (const path of SCREENS) {
      await page.goto(path);
      await expect(page.locator("main h1")).toBeVisible();
      await expectAccessible(page, `${path} (${scheme})`);
    }
  });
}

test("reflows at 320 px: nothing scrolls sideways", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await signIn(page);
  const job = posting("Reflow Tester", "Narrow Co");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  for (const path of [page.url(), "/applications", "/profiles/new", "/settings"]) {
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${path} scrolls sideways at 320 px`).toBeLessThanOrEqual(0);
  }
});

test("every control is at least 44 px", async ({ page }) => {
  await signIn(page);
  for (const path of ["/applications", "/settings", "/profiles/new"]) {
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    const small = await page.evaluate(() =>
      [...document.querySelectorAll<HTMLElement>("main button, main a[href], main input:not([type=checkbox]):not([type=radio]), main select, main [role=button]")]
        .filter((el) => el.offsetParent !== null)
        // A card's title link stretches over the whole card (after:inset-0): the card is its target.
        .filter((el) => !el.className.includes("after:inset-0"))
        .map((el) => ({ el, box: el.getBoundingClientRect() }))
        .filter(({ box }) => box.height < 44 - 0.5)
        .map(({ el, box }) => `${el.tagName} "${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30)}" ${box.height.toFixed(0)}px`));
    expect(small, path).toEqual([]);
  }
});

test("the skip link goes to the content", async ({ page }) => {
  await signIn(page);
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to the content" });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});
