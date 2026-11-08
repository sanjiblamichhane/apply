import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

import { OWNER } from "./owner";

export async function signIn(page: Page, locale: "en" | "ne" | "es" = "en") {
  await page.context().addCookies([{ name: "apply_locale", value: locale, url: "http://127.0.0.1:3399" }]);
  await page.goto("/sign-in");
  await page.locator("#email").fill(OWNER.email);
  await page.locator("#password").fill(OWNER.password);
  await page.locator("form button[type=submit]").click();
  await expect(page).toHaveURL(/\/today/);
  await page.goto("/applications");
  await expect(page.locator("main h1")).toBeVisible();
}

/** No WCAG 2.2 A or AA violations on the page as it is now. */
export async function expectAccessible(page: Page, label: string) {
  // Toasts are left out: axe catches them mid-fade, and their colours are the tokens the contrast test covers.
  // A document's preview runs no scripts (sandbox), so axe can't run inside it: with one on the page, axe checks
  // the page around it (the frame has a title), and the page in it is checked on its own (expectPageAccessible).
  const sandboxed = (await page.locator("iframe[sandbox]").count()) > 0;
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .exclude("[data-sonner-toaster]").setLegacyMode(sandboxed).analyze();
  const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.help}\n  ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join("\n  ")}`);
  expect(summary, `${label}: accessibility violations`).toEqual([]);
}

/** A document's page (or a template's sample) on its own, against WCAG 2.2 AA, as a reader would open it. */
export async function expectPageAccessible(from: Page, html: string, label: string) {
  const page = await from.context().newPage();
  try {
    await page.setContent(html);
    await expectAccessible(page, label);
  } finally {
    await page.close();
  }
}

let counter = 0;
/** A posting no other test has used: each journey makes its own opportunity. */
export function posting(title = "Senior Backend Engineer", company = "Acme Robotics"): { title: string; text: string } {
  counter += 1;
  const unique = `${title} ${Date.now() % 100000}-${counter}`;
  return {
    title: unique,
    text: `${unique} at ${company}\nWe build fleet software in Python and Django on PostgreSQL.\nYou will design APIs and own reliability.\nRequirements: 5+ years Python, PostgreSQL, Celery.`,
  };
}

export async function addProfile(page: Page, name = "Backend") {
  await page.goto("/profiles/new");
  await page.getByLabel(/Profile name|प्रोफाइलको नाम/).fill(name);
  await page.getByLabel(/Full name|पूरा नाम/).fill("Sam Rai");
  await page.getByLabel(/^Title$|^पद$/).first().fill("Backend Engineer");
  await page.getByLabel(/^Organisation$|^संस्था$/).first().fill("Himal Tech");
  await page.getByLabel(/What you did|तपाईंले गरेका काम/).first().fill("Built Django REST APIs on PostgreSQL\nMoved slow work to Celery");
  await page.getByLabel(/^Skills$|^सीपहरू$/).fill("Python\nDjango\nPostgreSQL");
  await page.locator("form button[type=submit]").click();
  await expect(page).toHaveURL(/\/profiles$/);
}
