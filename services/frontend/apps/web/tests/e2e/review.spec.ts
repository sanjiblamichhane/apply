import { expect, test } from "@playwright/test";

import { addProfile, expectAccessible, expectPageAccessible, posting, signIn } from "./helpers";

/** Review: apply anywhere by hand with reviewed documents. */
test("review a resume, preview it in the template, download it, and send it by hand with the kit", async ({ page }) => {
  await signIn(page);
  await addProfile(page, "Review");
  await page.goto("/applications");
  const job = posting("Platform Engineer", "Example Retail");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();

  await page.getByRole("button", { name: /^Write it\W+Resume$/ }).click();
  const resume = page.getByRole("article", { name: /Resume/ });
  await expect(resume.getByRole("heading", { name: /Check these before you send it/ })).toBeVisible();
  await expect(resume.getByText("Led a team of 12 engineers").first()).toBeVisible();
  await expect(resume.getByText("Not in your profile")).toBeVisible();
  await expect(resume.getByText("A number your profile doesn't have")).toBeVisible();
  await expectAccessible(page, "review");

  // The number is "true" (the person says so); the invented sentence is edited out: version 2, checked again.
  await resume.getByRole("button", { name: /^It's true\W+12/ }).click();
  await expect(resume.getByText("You said it's true")).toBeVisible();
  await resume.getByRole("button", { name: "Edit" }).click();
  const editor = resume.getByRole("textbox", { name: "Edit" });
  const text = await editor.inputValue();
  await editor.fill(text.replace("- Led a team of 12 engineers\n", ""));
  await resume.getByRole("button", { name: "Save as a new version" }).click();
  await expect(page.getByText("Saved as version 2").first()).toBeVisible();
  await expect(resume.getByText("Version 2")).toBeVisible();
  await expect(resume.getByText("Everything here is backed by your profile.")).toBeVisible();

  await resume.getByRole("checkbox", { name: /I've read it and it's true/ }).check();
  await expect(resume.getByText(/Reviewed/)).toBeVisible();

  // Seen first, as it will be downloaded: the page in the template, then the PDF (that page printed) or the page.
  await resume.getByRole("button", { name: /^Preview\W+Resume$/ }).click();
  const preview = page.getByRole("dialog", { name: "Resume, Version 2" });
  const frame = preview.frameLocator("iframe");
  await expect(frame.getByRole("heading", { level: 1, name: "Sam Rai" })).toBeVisible();
  await expectAccessible(page, "preview");
  let download = page.waitForEvent("download");
  await preview.getByRole("button", { name: "Download PDF" }).click();
  expect((await download).suggestedFilename()).toMatch(/resume-v2\.pdf$/);
  download = page.waitForEvent("download");
  await preview.getByRole("button", { name: "Download web page (.html)" }).click();
  const html = await download;
  expect(html.suggestedFilename()).toMatch(/resume-v2\.html$/);
  const { readFile } = await import("node:fs/promises");
  await expectPageAccessible(page, await readFile((await html.path())!, "utf8"), "the resume's page");
  await preview.getByRole("button", { name: "Close" }).click();

  // The kit: the form, the documents (reviewed), the answers, then "I've submitted it".
  const kit = page.getByRole("region", { name: "Application kit" });
  await expect(kit.getByText("Resume")).toBeVisible();
  await expect(kit.getByText(/Reviewed/)).toBeVisible();
  await kit.getByRole("button", { name: "I've submitted it" }).click();
  await expect(kit.getByText(/Recorded as sent/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Stage: In progress" })).toBeVisible();
  await kit.getByRole("button", { name: "Undo" }).click();
  await expect(kit.getByRole("button", { name: "I've submitted it" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Stage: New" })).toBeVisible();
  await expectAccessible(page, "kit");
});

test("saved answers: the common questions are there, sensitive ones declined", async ({ page }) => {
  await signIn(page);
  await page.goto("/answers");
  await expect(page.getByRole("heading", { level: 1, name: "Saved answers" })).toBeVisible();
  await expect(page.getByText("Gender (equal-opportunity question)")).toBeVisible();
  const gender = page.getByRole("combobox", { name: "Gender (equal-opportunity question)" });
  await expect(gender).toHaveValue("decline");
  const notice = page.getByRole("textbox", { name: "What is your notice period?" });
  await notice.fill("One month");
  await notice.press("Enter");
  await expect(page.getByText("Answer saved").first()).toBeVisible();
  await page.getByRole("radio", { name: "Yes" }).first().check();
  await expectAccessible(page, "answers");
});
