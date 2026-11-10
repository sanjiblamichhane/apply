import { expect, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";
import { OWNER } from "./owner";

test("a page needs signing in, and comes back after", async ({ page }) => {
  await page.goto("/profiles");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fprofiles/);
  await expect(page.getByRole("heading", { level: 1, name: "Sign in" })).toBeVisible();
  await expectAccessible(page, "sign-in");
  await page.locator("#email").fill(OWNER.email);
  await page.locator("#password").fill(OWNER.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/profiles$/);
});

test("a wrong password is said, in words", async ({ page }) => {
  await page.goto("/sign-in");
  await page.locator("#email").fill(OWNER.email);
  await page.locator("#password").fill("not the password at all");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "don't match" })).toBeVisible();
  await expect(page.locator("#password")).toHaveAttribute("aria-invalid", "true");
});

test("signing out ends the session", async ({ page }) => {
  await signIn(page);
  // Above it, the apply this is, linking to the releases so people can tell when to update.
  const version = page.getByRole("link", { name: /^Version \d+\.\d+\.\d+ ?, what's new, in a new tab$/ });
  await expect(version).toHaveAttribute("href", "https://github.com/sanjiblamichhane/apply/releases");
  await expect(version).toHaveAttribute("target", "_blank");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in/);
  await page.goto("/applications");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("the password can be shown and hidden", async ({ page }) => {
  await page.goto("/sign-in");
  const toggle = page.getByRole("button", { name: "Show the password" });
  await toggle.click();
  await expect(page.locator("#password")).toHaveAttribute("type", "text");
  await expect(page.getByRole("button", { name: "Hide the password" })).toHaveAttribute("aria-pressed", "true");
});
