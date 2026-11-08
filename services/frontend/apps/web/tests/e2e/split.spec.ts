import { expect, test } from "@playwright/test";

import { expectAccessible, posting, signIn } from "./helpers";

// Short, so the application's detail is longer than the screen.
test.use({ viewport: { width: 1440, height: 600 } });

test("an application beside the board: each side scrolls on its own, and the page stays still", async ({ page }) => {
  await signIn(page);
  const job = posting("Platform Engineer", "Yeti Cloud");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Notes" })).toBeAttached();

  const page_ = page.locator("#page-scroller");
  const list = page.getByTestId("split-primary");
  const detail = page.getByTestId("split-detail");
  await expect(list).toBeVisible();
  // The split fills the screen and no more: the page itself has nothing to scroll.
  expect(await page_.evaluate((el) => el.scrollHeight - el.clientHeight)).toBeLessThanOrEqual(1);
  expect(await detail.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);

  // Scrolling over the detail moves only the detail.
  const box = (await detail.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.wheel(0, 1500);
  await expect.poll(() => detail.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
  expect(await list.evaluate((el) => el.scrollTop)).toBe(0);
  expect(await page_.evaluate((el) => el.scrollTop)).toBe(0);
  await expect(page.getByRole("heading", { level: 2, name: "Notes" })).toBeInViewport();

  // And over the board, only the board (when it's longer than the screen); the detail stays where it was.
  const scrolled = await detail.evaluate((el) => el.scrollTop);
  const listBox = (await list.boundingBox())!;
  await page.mouse.move(listBox.x + 40, listBox.y + listBox.height / 2);
  await page.mouse.wheel(0, 800);
  await page.waitForTimeout(200);
  expect(await detail.evaluate((el) => el.scrollTop)).toBe(scrolled);
  expect(await page_.evaluate((el) => el.scrollTop)).toBe(0);
  await expectAccessible(page, "the split, scrolled");
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
