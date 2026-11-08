import { expect, test } from "@playwright/test";

import { addProfile, expectAccessible, signIn } from "./helpers";

test("profiles: create, edit, delete", async ({ page }) => {
  await signIn(page);
  await page.goto("/profiles/new");
  await expectAccessible(page, "new profile");
  await addProfile(page, "Data work");
  await page.getByRole("link", { name: "Data work" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Data work" })).toBeVisible();

  await page.getByLabel("Summary").fill("Analyst who turns SQL into decisions.");
  await page.getByRole("button", { name: "Add a role" }).click();
  await expect(page.getByRole("group", { name: "Role 2" })).toBeVisible();
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Profile saved").first()).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Summary")).toHaveValue("Analyst who turns SQL into decisions.");

  // The header stays at the top while the form scrolls, so Save is always there; its buttons are icons, named
  // in a tooltip on hover.
  await page.locator("#page-scroller").evaluate((el) => el.scrollTo(0, el.scrollHeight));
  await expect(page.getByRole("button", { name: "Save" })).toBeInViewport();
  await expect(page.getByRole("heading", { level: 1, name: "Data work" })).toBeInViewport();
  await page.getByRole("button", { name: "Duplicate" }).hover();
  await expect(page.getByRole("tooltip", { name: "Duplicate" })).toBeVisible();
  await expectAccessible(page, "a profile, scrolled, with a tooltip");

  await page.getByRole("button", { name: "Delete" }).click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.getByRole("alertdialog").getByRole("button", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/profiles$/);
  await expect(page.getByRole("link", { name: "Data work" })).toHaveCount(0);
  await expectAccessible(page, "profiles");
});

const RESUME = `Asha Gurung
Email: asha@example.com
Skills: Python, FastAPI, PostgreSQL
Experience: Data Engineer at Everest Analytics
- Built nightly pipelines in Python
- Cut report times from hours to minutes
`;

test("a resume becomes a profile, read by the model; then a copy to change what's different", async ({ page }) => {
  await signIn(page);
  await page.goto("/profiles/new");
  const start = page.getByRole("region", { name: "Start from your resume" });
  await expect(start.getByText("PDF, .docx or text, up to 5 MB.", { exact: false })).toBeVisible();
  await expectAccessible(page, "new profile, with the upload");

  await page.locator("input[type=file]").setInputFiles({ name: "asha-cv.txt", mimeType: "text/plain", buffer: Buffer.from(RESUME) });
  await expect(page).toHaveURL(/\/profiles\/[0-9A-Z]{26}$/);
  await expect(page.getByRole("status").filter({ hasText: "Reading asha-cv.txt…" })).toBeVisible();
  await expectAccessible(page, "a resume being read");

  await expect(page.getByText("Filled in from asha-cv.txt")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("heading", { level: 1, name: "Asha Gurung" })).toBeVisible();
  await expect(page.getByLabel("Full name")).toHaveValue("Asha Gurung");
  await expect(page.getByLabel(/What you did/).first()).toHaveValue("Built nightly pipelines in Python\nCut report times from hours to minutes");
  await expect(page.getByRole("link", { name: "Download asha-cv.txt" })).toHaveAttribute("href", /\/api\/v1\/profiles\/[0-9A-Z]{26}\/source$/);
  await expectAccessible(page, "a profile read from a resume");

  // Checked and saved: the reminder to check goes; the file stays a download away.
  await page.getByLabel("Summary").fill("Data engineer who makes reports fast.");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Profile saved").first()).toBeVisible();
  await expect(page.getByText("Filled in from asha-cv.txt")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Download asha-cv.txt" })).toBeVisible();

  // A copy for different roles: everything carried over, then only what's different changed.
  const original = page.url();
  await page.getByRole("button", { name: "Duplicate" }).click();
  await expect(page.getByText("Copied. Change what's different, then save.").first()).toBeVisible();
  await expect(page).not.toHaveURL(original);
  await expect(page.getByRole("heading", { level: 1, name: "Asha Gurung (copy)" })).toBeVisible();
  await expect(page.getByLabel("Summary")).toHaveValue("Data engineer who makes reports fast.");
  await page.getByLabel("Profile name").fill("Asha: analytics roles");
  await page.getByLabel("Summary").fill("Analytics engineer.");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Profile saved").first()).toBeVisible();

  await page.goto(original);
  await expect(page.getByLabel("Summary")).toHaveValue("Data engineer who makes reports fast.");
  await page.goto("/profiles");
  await expect(page.getByRole("link", { name: "Asha Gurung", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Asha: analytics roles" })).toBeVisible();
});

test("a file that can't be read says why, and nothing is made", async ({ page }) => {
  await signIn(page);
  await page.goto("/profiles/new");
  await page.locator("input[type=file]").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: Buffer.from("\x89PNG\r\n\x1a\n\0\0\0\0", "binary") });
  await expect(page.getByRole("alert").filter({ hasText: "apply reads PDF, .docx and text files." })).toBeVisible();
  await expect(page).toHaveURL(/\/profiles\/new$/);
  await expectAccessible(page, "an upload refused");
});
