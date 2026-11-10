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
  // And as Word, to edit: a real .docx (a zip with Word's document in it), its name the version's.
  await expect(preview.getByText(/The Word file is for editing/)).toBeVisible();
  download = page.waitForEvent("download");
  await preview.getByRole("button", { name: "Download Word (.docx)" }).click();
  const word = await download;
  expect(word.suggestedFilename()).toMatch(/resume-v2\.docx$/);
  const bytes = await readFile((await word.path())!);
  expect(bytes.subarray(0, 2).toString()).toBe("PK");
  expect(bytes.includes(Buffer.from("word/document.xml"))).toBe(true);
  await preview.getByRole("button", { name: "Close" }).click();

  // The kit: the form, the documents (reviewed), the answers, then "I've submitted it".
  await page.getByRole("tab", { name: "Application kit" }).click();
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

test("say a warning is wrong and what's true, then have it written again with the correction", async ({ page }) => {
  await signIn(page);
  await addProfile(page, "Rewrite");
  await page.goto("/applications");
  const job = posting("Data Engineer", "Example Foods");
  await page.getByLabel("Paste a job").fill(job.text);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  await page.getByRole("button", { name: /^Write it\W+Resume$/ }).click();
  const resume = page.getByRole("article", { name: /Resume/ });
  await expect(resume.getByRole("heading", { name: /Check these before you send it/ })).toBeVisible();

  // Each warning in its sentence, its words marked.
  const number = resume.getByRole("listitem").filter({ hasText: "A number your profile doesn't have" });
  await expect(number.locator("mark")).toHaveText("12 engineers");
  await expect(number.getByText("Led a team of 12 engineers")).toBeVisible();
  // Nothing to rewrite from yet: a disclosure.
  await expect(resume.getByRole("button", { name: /^Ask for changes/ })).toBeVisible();

  // "It's wrong": the field takes focus; Cancel gives it back; then what's true, saved.
  await number.getByRole("button", { name: /^It's wrong\W+12 engineers/ }).click();
  const field = number.getByRole("textbox", { name: "What's true instead?" });
  await expect(field).toBeFocused();
  await number.getByRole("button", { name: "Cancel" }).click();
  await expect(number.getByRole("button", { name: /^It's wrong/ })).toBeFocused();
  await number.getByRole("button", { name: /^It's wrong/ }).click();
  await field.fill("5 engineers");
  await field.press("Enter");
  await expect(number.getByText("You said it's wrong: 5 engineers")).toBeVisible();
  await expect(number.getByRole("button", { name: /^Look again/ })).toBeFocused();
  await expectAccessible(page, "review: a correction");

  // With a correction, the rewrite is open: notes are optional.
  const rewrite = resume.getByRole("form", { name: "Write it again with your changes" });
  await expect(rewrite.getByText(/Your corrections above go with it/)).toBeVisible();
  await rewrite.getByRole("textbox", { name: /Anything else to change/ }).fill("Keep it to one page.");
  await rewrite.getByRole("button", { name: /^Rewrite it/ }).click();
  await expect(resume.getByText(/Version 2 · Rewritten with your changes/)).toBeVisible();
  await expect(resume.getByText("Led a team of 5 engineers")).toBeVisible();
  // The corrected number is the person's own word now: nothing left to check.
  await expect(resume.getByText("Everything here is backed by your profile.")).toBeVisible();
  await expect(resume.getByRole("button", { name: /^Ask for changes/ })).toBeVisible();
  await expectAccessible(page, "review: rewritten");
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
