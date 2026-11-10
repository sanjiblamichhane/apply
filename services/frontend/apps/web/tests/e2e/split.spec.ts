import { expect, test } from "@playwright/test";

import { addProfile, expectAccessible, posting, signIn } from "./helpers";

// Short, so the application's detail is longer than the screen.
test.use({ viewport: { width: 1440, height: 500 } });

test("an application beside the board, wide, in tabs: each side scrolls on its own, the tabs stay in view", async ({ page }) => {
  await signIn(page);
  const job = posting("Platform Engineer", "Yeti Cloud");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();

  const page_ = page.locator("#page-scroller");
  const list = page.getByTestId("split-primary");
  const detail = page.getByTestId("split-detail");
  await expect(list).toBeVisible();
  // The detail is the wider side.
  const [listBox, detailBox] = [(await list.boundingBox())!, (await detail.boundingBox())!];
  expect(detailBox.width).toBeGreaterThan(listBox.width);
  // The split fills the screen and no more: the page itself has nothing to scroll.
  expect(await page_.evaluate((el) => el.scrollHeight - el.clientHeight)).toBeLessThanOrEqual(1);

  // Documents first; each part is a tab, so none is a long way down.
  const tabs = page.getByRole("tablist", { name: "This application's parts" });
  await expect(tabs.getByRole("tab", { name: "Documents", selected: true })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Notes" })).toHaveCount(0);

  // Scrolling over the detail moves only the detail, and the tabs stay in view.
  expect(await detail.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
  await page.mouse.move(detailBox.x + detailBox.width / 2, detailBox.y + detailBox.height / 2);
  await page.mouse.wheel(0, 1500);
  await expect.poll(() => detail.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
  await expect(tabs).toBeInViewport();
  expect(await list.evaluate((el) => el.scrollTop)).toBe(0);
  expect(await page_.evaluate((el) => el.scrollTop)).toBe(0);
  await expectAccessible(page, "the split, scrolled");

  // A tab is in the address: a reload keeps it. The arrow keys move between tabs.
  await tabs.getByRole("tab", { name: "Notes and history" }).click();
  await expect(page).toHaveURL(/\?tab=notes$/);
  await expect(page.getByRole("heading", { level: 2, name: "Notes" })).toBeVisible();
  await page.reload();
  await expect(tabs.getByRole("tab", { name: "Notes and history", selected: true })).toBeVisible();
  await tabs.getByRole("tab", { name: "Notes and history" }).focus();
  await page.keyboard.press("ArrowLeft");
  await expect(tabs.getByRole("tab", { name: "The job", selected: true })).toBeFocused();
  await expect(page.getByRole("region", { name: "The job" })).toBeVisible();
  await expect(page).toHaveURL(/\?tab=details$/);
  await expectAccessible(page, "the split, the job tab");
});

test("the detail closes with ✕; Delete takes the card away with Undo, then for good", async ({ page }) => {
  await signIn(page);
  const job = posting("Data Engineer", "Kanchan Labs");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  const card = page.getByTestId("split-primary").getByRole("link", { name: new RegExp(job.title) });
  await expect(card).toBeVisible();

  // ✕: back to the board alone, at its own address.
  await page.getByRole("link", { name: `Close: ${job.title}` }).click();
  await expect(page).toHaveURL(/\/applications$/);
  await expect(page.getByTestId("split-detail")).toHaveCount(0);

  // Delete, then Undo: it's back.
  await page.getByRole("link", { name: new RegExp(job.title) }).first().click();
  await page.getByRole("button", { name: new RegExp(`^Delete\\W+${job.title}$`) }).click();
  await expect(page).toHaveURL(/\/applications$/);
  await expect(page.getByRole("link", { name: new RegExp(job.title) })).toHaveCount(0);
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("link", { name: new RegExp(job.title) }).first()).toBeVisible();

  // Delete, and let Undo pass: gone, after a reload too.
  await page.getByRole("link", { name: new RegExp(job.title) }).first().click();
  await page.getByRole("button", { name: new RegExp(`^Delete\\W+${job.title}$`) }).click();
  const toast = page.locator("[data-sonner-toast]", { hasText: `Deleted: ${job.title}` });
  await expect(toast.first()).toBeVisible();
  await expect(toast).toHaveCount(0, { timeout: 15_000 }); // Undo's time passes: deleted for good
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: new RegExp(job.title) })).toHaveCount(0);
});

test.describe("on a laptop screen, with a resume written", () => {
  test.use({ viewport: { width: 1366, height: 768 } });

  test("the page never scrolls as well as the panel: what's hidden for screen readers stays inside it", async ({ page }) => {
    await signIn(page);
    await addProfile(page, "Laptop");
    await page.goto("/applications");
    const job = posting("Site Reliability Engineer", "Everest Data");
    await page.getByLabel("Paste a job").fill(job.text);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
    await page.getByRole("button", { name: /^Write it\W+Resume$/ }).click();
    await expect(page.getByRole("article", { name: /Resume/ }).getByText("Version 1")).toBeVisible();

    const detail = page.getByTestId("split-detail");
    expect(await detail.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    // One scroll for the application: the panel's. The page has nothing to scroll, at the top or the bottom.
    const pageScroll = () => page.locator("#page-scroller").evaluate((el) => el.scrollHeight - el.clientHeight);
    expect(await pageScroll()).toBeLessThanOrEqual(1);
    await detail.evaluate((el) => el.scrollTo(0, el.scrollHeight));
    expect(await pageScroll()).toBeLessThanOrEqual(1);
  });
});
