import { expect, test } from "@playwright/test";

import { addProfile, expectAccessible, signIn } from "./helpers";

/**
 * Discovery: a source and a saved search fill a ranked inbox, with no duplicates, and a match
 * becomes an application.
 */
test("a source and a search fill a ranked inbox; track one, dismiss one, undo", async ({ page }) => {
  await signIn(page);
  await addProfile(page, "Discovery");

  await page.goto("/sources/new");
  await expectAccessible(page, "new source");
  // A company's board, from its address: no list of platforms to choose from.
  await expect(page.getByRole("radio")).toHaveCount(0);
  await page.getByLabel("Job board address").fill("https://example.com/careers");
  await expect(page.getByText("apply doesn't recognise that address.", { exact: false })).toBeVisible();
  await page.getByLabel("Job board address").fill("https://boards.greenhouse.io/acme");
  await expect(page.getByText("Recognised: a company's job board.")).toBeVisible();
  await expect(page.getByLabel("Board name")).toHaveValue("acme");
  await expectAccessible(page, "new source, recognised");
  await page.getByRole("button", { name: "Add a source" }).click();
  await expect(page).toHaveURL(/\/sources$/);
  await expect(page.getByText(/2 postings, checked/)).toBeVisible();
  await expectAccessible(page, "sources");

  await page.goto("/searches/new");
  await page.getByLabel("Name", { exact: true }).fill("Python roles");
  await page.getByLabel("Words to look for").fill("python");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page).toHaveURL(/\/searches$/);
  await expect(page.getByRole("link", { name: "Python roles" })).toBeVisible();
  await expectAccessible(page, "searches");

  await page.goto("/matches");
  const card = page.getByRole("article", { name: "Senior Backend Engineer" });
  await expect(card.getByText("Fit 86 of 100")).toBeVisible();
  await expect(card.getByText("Strong fit")).toBeVisible();
  await expect(page.getByRole("article", { name: "Product Designer" })).toHaveCount(0);   // no python: not a match
  await expectAccessible(page, "matches");

  await card.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("article", { name: "Senior Backend Engineer" })).toHaveCount(0);
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("article", { name: "Senior Backend Engineer" })).toBeVisible();

  await page.getByRole("article", { name: "Senior Backend Engineer" }).getByRole("button", { name: "Track" }).click();
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  await expect(page.getByRole("heading", { level: 1, name: "Senior Backend Engineer" })).toBeVisible();

  await page.goto("/matches?status=tracked");
  await expect(page.getByRole("article", { name: "Senior Backend Engineer" }).getByRole("link", { name: "Open the application" })).toBeVisible();

  await page.goto("/today");
  await page.getByRole("button", { name: "Brief me now" }).first().click();
  await expect(page.getByRole("heading", { name: "New matches" })).toBeVisible();
  await expectAccessible(page, "today");
});

test("discovery screens in Nepali, and in dark", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await signIn(page, "ne");
  for (const [path, heading] of [["/today", "आज"], ["/matches", "मेल खाएका"], ["/searches", "खोजहरू"], ["/sources", "स्रोतहरू"],
                                 ["/sources/new", "स्रोत थप्नुहोस्"], ["/searches/new", "नयाँ खोज"]] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    await expectAccessible(page, `${path} (ne, dark)`);
  }
});
