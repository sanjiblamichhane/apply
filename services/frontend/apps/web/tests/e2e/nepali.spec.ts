import { expect, test } from "@playwright/test";

import { expectAccessible, posting, signIn } from "./helpers";

test("the whole flow in Nepali", async ({ page }) => {
  await signIn(page, "ne");
  await expect(page.locator("html")).toHaveAttribute("lang", "ne");
  await expect(page.getByRole("heading", { level: 1, name: "आवेदनहरू" })).toBeVisible();
  await expectAccessible(page, "board (ne)");

  const job = posting("Backend Engineer", "Leapfrog");
  await page.getByLabel("जागिर टाँस्नुहोस्").fill(job.text);
  await page.getByRole("button", { name: "थप्नुहोस्", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  await page.getByRole("button", { name: /^लेख्नुहोस्\W+बायोडाटा$/ }).click();
  const resume = page.getByRole("article", { name: /बायोडाटा/ });
  await expect(resume.getByText("संस्करण १")).toBeVisible();
  await page.getByRole("button", { name: /^चरण:/ }).click();
  await page.getByRole("menuitemradio", { name: "अन्तर्वार्ता" }).click();
  await expect(page.getByRole("button", { name: "चरण: अन्तर्वार्ता" })).toBeVisible();
  await expectAccessible(page, "detail (ne)");
});

test("switching language in Settings changes every screen and is remembered", async ({ page }) => {
  await signIn(page);
  await page.goto("/settings");
  await page.getByRole("radio", { name: "नेपाली" }).check();
  await expect(page.getByRole("heading", { level: 1, name: "सेटिङहरू" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "ne");
  await page.goto("/profiles");
  await expect(page.getByRole("heading", { level: 1, name: "प्रोफाइलहरू" })).toBeVisible();
  await page.goto("/settings");
  await page.getByRole("radio", { name: "English" }).check();
  await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
});
