import { expect, test } from "@playwright/test";

import { addProfile, expectAccessible, posting, signIn } from "./helpers";

/**
 * The core journey: sign in, paste a job, get a tailored resume and cover letter, and move the application
 * through its stages.
 */
test("paste a job, get both documents, move it through the pipeline", async ({ page }) => {
  await signIn(page);
  await addProfile(page);
  await page.goto("/applications");
  const job = posting();

  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  await expect(page.getByText("Acme Robotics").first()).toBeVisible();
  await expectAccessible(page, "application detail");

  // The resume: being written, then ready, from the profile.
  await page.getByRole("button", { name: /^Write it\W+Resume$/ }).click();
  await expect(page.getByRole("status").filter({ hasText: "Being written" })).toBeVisible();
  const resume = page.getByRole("article", { name: /Resume/ });
  await expect(resume.getByText("Version 1")).toBeVisible();
  await expect(resume.getByRole("heading", { name: "Sam Rai" })).toBeVisible();
  await expect(resume.getByText(/Himal Tech/)).toBeVisible();

  // The cover letter.
  await page.getByRole("button", { name: /^Write it\W+Cover letter$/ }).click();
  const letter = page.getByRole("article", { name: /Cover letter/ });
  await expect(letter.getByText("Version 1")).toBeVisible();
  await expect(letter.getByText(/Dear Hiring Manager/)).toBeVisible();

  // Writing again makes version 2, and version 1 stays until it's done.
  await resume.getByRole("button", { name: /Write again/ }).click();
  await expect(resume.getByText("Version 2")).toBeVisible();
  await resume.getByText("Versions").click();
  await expect(resume.getByText("Version 1")).toBeVisible();

  // Through the pipeline.
  for (const stage of ["Initial screening", "Interview"]) {
    await page.getByRole("button", { name: /^Stage:/ }).click();
    await page.getByRole("menuitemradio", { name: stage }).click();
    await expect(page.getByRole("button", { name: `Stage: ${stage}` })).toBeVisible();
  }
  const history = page.getByRole("region", { name: "History" });
  await expect(history.getByText("Entered Interview")).toBeVisible();
  await expect(history.getByText("Entered New")).toBeVisible();

  // On the board, in its column, with both documents ready.
  await page.goto("/applications");
  const column = page.getByRole("region", { name: /^Interview/ });
  const card = column.getByRole("article").filter({ hasText: job.title });
  await expect(card).toBeVisible();
  await expect(card.getByText(/Resume/)).toBeVisible();
  await expectAccessible(page, "board");
});

test("the same posting pasted twice opens the one already tracked", async ({ page }) => {
  await signIn(page);
  const job = posting("Data Analyst", "Example Retail");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  const first = page.url();
  await page.goto("/applications");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page).toHaveURL(first);
  await expect(page.getByText("You added this one before")).toBeVisible();
});

test("a stage can be changed from the board with the keyboard alone", async ({ page }) => {
  await signIn(page);
  const job = posting("Platform Engineer", "Himalaya Cloud");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.keyboard.press("ControlOrMeta+Enter");
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  await page.goto("/applications");

  const move = page.getByRole("button", { name: `Move “${job.title}” to…` });
  await move.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("menu")).toBeVisible();
  const offer = page.getByRole("menuitemradio", { name: "Offer" });
  await offer.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Moved to Offer").first()).toBeVisible();
  await expect(page.getByRole("region", { name: /^Offer/ }).getByText(job.title)).toBeVisible();
});

test("list view and the filter live in the URL", async ({ page }) => {
  await signIn(page);
  const job = posting("Site Reliability Engineer", "Example Analytics");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page).toHaveURL(/\/applications\/[0-9A-Z]{26}$/);
  await page.goto("/applications");
  await page.getByRole("button", { name: "List" }).click();
  await expect(page).toHaveURL(/view=list/);
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByLabel("Filter applications").fill("nothing-matches-this");
  await expect(page).toHaveURL(/q=nothing-matches-this/);
  await expect(page.getByText("Nothing matches")).toBeVisible();
  await page.getByLabel("Filter applications").fill("");
  // Switching view is a step back can undo; typing in the filter isn't (it replaces, not stacks).
  await page.getByRole("button", { name: "Board" }).click();
  await expect(page.getByRole("region", { name: "Applications" })).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/view=list/);
  await expect(page.getByRole("table")).toBeVisible();
  await expectAccessible(page, "list view");
});
