/**
 * The README's pictures of the web app: John Doe's applications, one with its documents, Today, and Settings →
 * Model, in light and dark. Written to demo/images at the repo's root.
 */
import { fileURLToPath } from "node:url";

import { OWNER } from "@apply/e2e-harness";
import { expect, type Page, test } from "@playwright/test";

const IMAGES = fileURLToPath(new URL("../../../../../../demo/images/", import.meta.url));

async function signIn(page: Page) {
  await page.context().addCookies([{ name: "apply_locale", value: "en", url: "http://127.0.0.1:3397" }]);
  await page.goto("/sign-in");
  await page.locator("#email").fill(OWNER.email);
  await page.locator("#password").fill(OWNER.password);
  await page.locator("form button[type=submit]").click();
  await expect(page).toHaveURL(/\/today/);
}

/** Settled: no spinners, fonts in, nothing animating. */
async function shot(page: Page, name: string) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${IMAGES}${name}.png` });
}

for (const scheme of ["light", "dark"] as const) {
  test(`the web app, ${scheme}`, async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: scheme, viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
    const page = await context.newPage();
    await signIn(page);
    const suffix = scheme === "dark" ? "-dark" : "";

    await page.goto("/applications");
    await expect(page.getByText("Senior Lorem Engineer").first()).toBeVisible();
    await shot(page, `web-applications${suffix}`);
    if (scheme === "dark") return;

    await page.getByText("Senior Lorem Engineer").first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Senior Lorem Engineer" })).toBeVisible();
    await expect(page.getByText(/Dear Hiring Manager|John Doe/).first()).toBeVisible();
    await shot(page, "web-application");

    await page.goto("/today");
    await expect(page.locator("main h1")).toBeVisible();
    await shot(page, "web-today");

    await page.goto("/settings");
    const model = page.getByRole("region", { name: "Model" });
    await expect(model.getByText("writer:8b").first()).toBeVisible();
    await model.scrollIntoViewIfNeeded();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    await model.screenshot({ path: `${IMAGES}web-model-settings.png` });
    await context.close();
  });
}
