import { expect, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";

test("make a token for the extension, see it once, and revoke it", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await signIn(page);
  await page.goto("/settings");
  const section = page.getByRole("region", { name: "Browser extension" });
  await expect(section).toBeVisible();
  await section.getByLabel("Name").fill("Browser on the laptop");
  await expect(section.getByLabel("Record what you've submitted")).toBeChecked();
  await expect(section.getByRole("radio", { name: "Never" })).toBeChecked(); // stays connected until revoked
  await section.getByRole("button", { name: "Make a token" }).click();

  const secret = section.getByLabel("Copy your token now");
  await expect(secret).toHaveValue(/^apl_/);
  const value = await secret.inputValue();
  await section.getByRole("button", { name: "Copy token" }).click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(value);
  await expectAccessible(page, "settings: a new token");

  await section.getByRole("button", { name: "Done" }).click();
  await expect(section.getByLabel("Copy your token now")).toHaveCount(0); // shown once only
  const row = section.getByRole("listitem").filter({ hasText: "Browser on the laptop" });
  await expect(row).toBeVisible();
  await expect(row.getByText(/Not used yet/)).toBeVisible();
  await expect(row.getByText(/Doesn't expire/)).toBeVisible();

  // It works until revoked.
  const me = await page.request.get("/api/v1/tokens/current", { headers: { Authorization: `Bearer ${value}` } });
  expect(me.status()).toBe(200);
  await section.getByRole("button", { name: "Revoke Browser on the laptop" }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog.getByText("can't be undone")).toBeVisible();
  await expectAccessible(page, "settings: revoke a token");
  await dialog.getByRole("button", { name: "Revoke" }).click();
  await expect(row.getByText("Revoked", { exact: true })).toBeVisible();
  const after = await page.request.get("/api/v1/tokens/current", { headers: { Authorization: `Bearer ${value}` } });
  expect(after.status()).toBe(401);
});
