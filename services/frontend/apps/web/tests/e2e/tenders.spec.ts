import { expect, type Page, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";

/**
 * More packs, in the browser: a second pack end to end with no screen code of its own. Switch to
 * Tenders, make an organisation profile with the form drawn from the pack's schema, paste a tender, have the
 * capability statement written, and move it to "Submitted". The pack choice lives in this browser context only.
 */
let counter = 0;
function tender() {
  counter += 1;
  const title = `Case management software ${Date.now() % 100000}-${counter}`;
  return { title, text: `${title} at Example City Council\nA hosted case management system.\nSuppliers must hold Cyber Essentials Plus.` };
}

async function switchTo(page: Page, label: RegExp, pack: string) {
  await page.getByLabel(label).selectOption({ label: pack });
}

test("tenders: an organisation profile, a pasted tender, a capability statement, submitted", async ({ page }) => {
  await signIn(page);
  await switchTo(page, /^Working on$/, "Tenders");

  // The profile: the pack's own fields, with a list of past contracts to add to.
  await page.goto("/profiles/new");
  await expect(page.getByLabel("Full name")).toHaveCount(0); // that's the job pack's form
  await page.getByLabel("Profile name").fill("Example Software");
  await page.getByLabel("Legal name").fill("Example Software Ltd");
  await page.getByLabel("What you do").fill("Hosted case management\nData migration from legacy systems");
  await page.getByRole("button", { name: "Add to Past contracts" }).click();
  const past = page.getByRole("group", { name: "Past contracts 1" });
  await past.getByLabel("Client").fill("Example Borough Council");
  await past.getByLabel("What it was").fill("Adult social care case system");
  await expectAccessible(page, "tenders: new profile");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page).toHaveURL(/\/profiles$/);
  await expect(page.getByText("Example Software").first()).toBeVisible();

  // Paste a tender: read by the model into the tender's fields.
  await page.goto("/applications");
  const notice = tender();
  await page.getByLabel("Paste a tender").fill(notice.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  await expect(page.getByRole("heading", { level: 1, name: notice.title })).toBeVisible();
  const details = page.getByRole("region", { name: "The tender" });
  await expect(details.getByText("Example City Council")).toBeVisible();
  await expect(details.getByText("Buyer")).toBeVisible();

  // The capability statement, written from the organisation's profile.
  await page.getByRole("button", { name: /^Write it\W+Capability statement$/ }).click();
  const statement = page.getByRole("article", { name: /Capability statement/ });
  await expect(statement.getByText("Version 1")).toBeVisible();
  await expect(statement.getByRole("heading", { name: "Example Software Ltd" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Write it\W+Tender response$/ })).toBeVisible();

  // Through the bid pipeline.
  await expect(page.getByRole("button", { name: "Stage: Identified" })).toBeVisible();
  await page.getByRole("button", { name: /^Stage:/ }).click();
  await page.getByRole("menuitemradio", { name: "Submitted" }).click();
  await expect(page.getByRole("button", { name: "Stage: Submitted" })).toBeVisible();
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await expectAccessible(page, `tenders: application detail (${scheme})`);
  }
  await page.emulateMedia({ colorScheme: "light" });

  // Edit what was read, with the same generic form.
  await details.getByRole("button", { name: "Edit the details" }).click();
  await details.getByLabel("Reference").fill("ECC-2026-0142");
  await details.getByRole("button", { name: "Save" }).click();
  await expect(details.getByText("ECC-2026-0142")).toBeVisible();

  // Only what means something for tenders: no remote, no visas, no Auto; Contracts Finder as a source.
  await page.goto("/searches/new");
  await expect(page.getByLabel("Places")).toBeVisible();
  await expect(page.getByLabel("Remote only")).toHaveCount(0);
  await expect(page.getByLabel("I need visa sponsorship")).toHaveCount(0);
  await expect(page.getByText("Prepare strong matches")).toHaveCount(0);
  await page.goto("/sources/new");
  await expect(page.getByRole("radio", { name: /Contracts Finder/ })).toBeChecked();
  await expect(page.getByLabel("Job board address")).toHaveCount(0); // the tender pack has no company boards

  // The board shows the tender pipeline; switching back to Jobs hides it.
  await page.goto("/applications");
  await expect(page.getByRole("region", { name: /^Submitted/ }).getByText(notice.title)).toBeVisible();
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await expectAccessible(page, `tenders: board (${scheme})`);
  }
  await switchTo(page, /^Working on$/, "Jobs");
  await expect(page.getByLabel("Paste a job")).toBeVisible();
  await expect(page.getByText(notice.title)).toHaveCount(0);
});

test("tenders in Nepali", async ({ page }) => {
  await signIn(page, "ne");
  await switchTo(page, /^काम गर्दै$/, "बोलपत्रहरू");
  await page.goto("/profiles/new");
  await expect(page.getByLabel("कानुनी नाम")).toBeVisible();
  await expect(page.getByRole("button", { name: "पहिलेका ठेक्काहरू मा थप्नुहोस्" })).toBeVisible();
  await expectAccessible(page, "tenders, Nepali: new profile");

  await page.goto("/applications");
  const notice = tender();
  await page.getByLabel("बोलपत्र टाँस्नुहोस्").fill(notice.text);
  await page.locator("form button[type=submit]").first().click();
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  const details = page.getByRole("region", { name: "बोलपत्र" });
  await expect(details.getByText("Example City Council")).toBeVisible();
  await expect(details.getByText("खरिदकर्ता")).toBeVisible();
  await expect(page.getByRole("button", { name: /पहिचान गरिएको$/ })).toBeVisible();
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await expectAccessible(page, `tenders, Nepali: application detail (${scheme})`);
  }
});
