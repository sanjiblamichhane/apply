import { expect, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";

/** Signing in and the first run: glass, English whatever the browser chose before, no language switch here. */
for (const scheme of ["light", "dark"] as const) {
  test(`sign in and create-your-account on glass, in English, pass axe (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    // A browser that chose Nepali before still gets the sign-in page in English.
    await page.context().addCookies([{ name: "apply_locale", value: "ne", url: "http://127.0.0.1:3399" }]);
    await page.goto("/sign-in");
    await expect(page.getByRole("heading", { level: 1, name: "Sign in" })).toBeVisible();
    await expect(page.locator("main")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("radio")).toHaveCount(0); // no language switch
    // This install has its owner: anyone else may make their own account (until the owner closes it).
    await expect(page.getByRole("link", { name: "Create an account" })).toBeVisible();
    const panel = page.getByRole("region", { name: "Sign in" });
    expect(await panel.evaluate((el) => getComputedStyle(el).backdropFilter)).toContain("blur");
    await expectAccessible(page, `sign-in (${scheme})`);

    // Closed by the owner: the page says so and points to sign-in.
    await page.route("**/api/v1/auth/setup", (route) => route.fulfill({ json: { open: false, first_run: false } }));
    await page.goto("/register");
    await expect(page.getByText(/New accounts are closed here/)).toBeVisible();
    await expectAccessible(page, `register, closed (${scheme})`);

    // The form itself, as a fresh install shows it (the API's answer stood in for; it still refuses for real).
    await page.unrouteAll();
    await page.route("**/api/v1/auth/setup", (route) => route.fulfill({ json: { open: true, first_run: true } }));
    await page.route("**/api/v1/auth/register", (route) => route.fulfill({
      status: 403, contentType: "application/problem+json",
      json: { type: "urn:apply:error:permission-denied", status: 403, title: "x", detail: "x", code: "REGISTRATION_CLOSED" },
    }));
    await page.goto("/register");
    await expect(page.getByRole("heading", { level: 1, name: "Create your account" })).toBeVisible();
    await page.getByLabel("Email").fill("someone@example.com");
    await page.getByLabel("Password", { exact: true }).fill("short");
    await page.getByLabel("The password again").fill("different");
    await page.getByRole("button", { name: "Create the account" }).click();
    await expect(page.getByText("The two passwords aren't the same.")).toBeVisible();
    await expect(page.getByRole("checkbox", { name: "Add a sample profile to look around" })).not.toBeChecked();
    await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("aria-invalid", "true");
    await expectAccessible(page, `register, form (${scheme})`);
    await page.getByLabel("Password", { exact: true }).fill("a long enough password");
    await page.getByLabel("The password again").fill("a long enough password");
    await page.getByRole("button", { name: "Create the account" }).click();
    await expect(page.getByText(/New accounts are closed here/)).toBeVisible();
  });
}

test("the sign-in page offers the owner's account on the first run, anyone's after", async ({ page }) => {
  await page.route("**/api/v1/auth/setup", (route) => route.fulfill({ json: { open: true, first_run: true } }));
  await page.goto("/sign-in");
  await page.getByRole("link", { name: "Create your account" }).click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByText(/This account owns apply on this machine/)).toBeVisible();
});

test("glass turns solid for anyone who asks for less transparency or more contrast", async ({ page }) => {
  await page.goto("/sign-in");
  const panel = page.getByRole("region", { name: "Sign in" });
  await expect(panel).toBeVisible();
  // The test browser has no switch for prefers-reduced-transparency yet: check the rule is there, with prefers-contrast's.
  const rules = await page.evaluate(() => [...document.styleSheets].flatMap((sheet) => {
    try { return [...sheet.cssRules].map((r) => r.cssText); } catch { return []; }
  }).filter((text) => text.includes("prefers-reduced-transparency") || text.includes("prefers-contrast")).join("\n"));
  expect(rules).toContain("prefers-reduced-transparency: reduce");
  expect(rules).toContain("prefers-contrast: more");
});

test("each page's ? opens its guide beside the page, which narrows to make room, in the reader's language", async ({ page }) => {
  await signIn(page);
  await page.goto("/sources");
  const main = page.locator("main");
  const before = (await main.boundingBox())!;
  await page.getByRole("button", { name: "Help: Sources" }).click();
  // Wide (1280 px): docked as a column of the layout, not a sheet over the page.
  const guide = page.getByRole("complementary", { name: "Sources" });
  await expect(guide).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(guide.getByRole("heading", { level: 2, name: "Sources" })).toBeFocused();
  const panel = (await guide.boundingBox())!;
  const after = (await main.boundingBox())!;
  expect(after.width).toBeLessThan(before.width - 300); // the page narrowed…
  expect(after.x + after.width).toBeLessThanOrEqual(panel.x + 1); // …so nothing is under the guide
  expect(panel.width).toBeLessThanOrEqual(360); // 22 rem
  expect(after.width).toBeGreaterThanOrEqual(640); // and the page keeps 40 rem
  await expect(page.getByRole("heading", { level: 1, name: "Sources" })).toBeVisible();
  await expectAccessible(page, "a guide docked");
  await guide.getByRole("link", { name: "Searches" }).click(); // guides link to each other in place
  await expect(page.getByRole("complementary", { name: "Searches" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("complementary", { name: "Searches" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Help: Sources" })).toBeFocused();
  expect((await main.boundingBox())!.width).toBeCloseTo(before.width, 0);

  // Close does the same.
  await page.getByRole("button", { name: "Help: Sources" }).click();
  await page.getByRole("complementary", { name: "Sources" }).getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("complementary", { name: "Sources" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Help: Sources" })).toBeFocused();

  // In Nepali, the guide is too.
  await page.goto("/settings");
  await page.getByRole("radio", { name: "नेपाली" }).check();
  await page.getByRole("button", { name: "सहायता: सेटिङहरू" }).click();
  const ne = page.getByRole("complementary", { name: "सेटिङहरू" });
  await expect(ne.getByRole("heading", { level: 2 })).toHaveAttribute("lang", "ne");
  await page.keyboard.press("Escape");
  await page.getByRole("radio", { name: "English" }).check();
});

test.describe("on a narrower screen", () => {
  test.use({ viewport: { width: 1024, height: 720 } });

  test("the guide is a sheet over the page's edge, which leaves the page usable", async ({ page }) => {
    await signIn(page);
    await page.goto("/sources");
    await page.getByRole("button", { name: "Help: Sources" }).click();
    const guide = page.getByRole("dialog", { name: "Sources" });
    await expect(guide).toBeVisible();
    await expect(guide.getByRole("heading", { level: 2, name: "Sources" })).toBeFocused();
    expect((await guide.boundingBox())!.width).toBeLessThanOrEqual(384); // 24 rem
    await expectAccessible(page, "a guide as a sheet");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Help: Sources" })).toBeFocused();
  });
});
