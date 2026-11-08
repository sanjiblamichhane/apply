import { expect, test } from "@playwright/test";

import { expectAccessible, expectPageAccessible, signIn } from "./helpers";

/**
 * Document templates: the defaults pass WCAG 2.2 AA as pages of their own; an upload with problems is refused
 * with each said; one within the rules is previewed, then used; and back to the default, with Undo.
 */
test("upload a document template: checked, previewed, used, and back to the default", async ({ page }) => {
  await signIn(page);
  await page.goto("/settings");
  const section = page.getByRole("region", { name: "Document templates" });
  const resumes = section.getByRole("listitem").filter({ hasText: "Resume" });
  await expect(resumes.getByText("The default template")).toBeVisible();

  await resumes.getByRole("button", { name: /^Preview\W+Resume$/ }).click();
  const sample = page.getByRole("dialog", { name: "Resume: a sample" });
  await expect(sample.frameLocator("iframe").getByRole("heading", { level: 2, name: "Professional Summary" })).toBeVisible();
  await expectAccessible(page, "a template's sample");
  await expect(sample.locator("iframe")).toHaveAttribute("title", "Resume: a sample");
  await sample.getByRole("button", { name: "Close" }).click();

  const download = page.waitForEvent("download");
  await resumes.getByRole("button", { name: /^Download template\W+Resume$/ }).click();
  const { readFile } = await import("node:fs/promises");
  const boilerplate = await readFile((await (await download).path())!, "utf8");
  expect(boilerplate).toContain("{{content}}");

  // Pale text and a script: refused, each problem said, nothing kept.
  const file = resumes.locator('input[type="file"]');
  const bad = boilerplate.replace("--text: #000000", "--text: #9a9a9a").replace("<main>", "<main>\n  <script>alert(1)</script>");
  await file.setInputFiles({ name: "pale.html", mimeType: "text/html", buffer: Buffer.from(bad) });
  const check = page.getByRole("dialog", { name: "Checking pale.html" });
  await expect(check.getByText(/needs 4\.5:1/).first()).toBeVisible();
  await expect(check.getByText("WCAG 1.4.3").first()).toBeVisible();
  await expect(check.getByText(/<script> isn't allowed/)).toBeVisible();
  await expect(check.getByRole("button", { name: "Use this template" })).toHaveCount(0);
  await expectAccessible(page, "a template's problems");

  // Green instead of blue: passes, previewed, used.
  const green = boilerplate.replace("--accent: #1f3864", "--accent: #0b4f2c");
  const chooser = page.waitForEvent("filechooser");
  await check.getByRole("button", { name: "Choose another file" }).click();
  await (await chooser).setFiles({ name: "green.html", mimeType: "text/html", buffer: Buffer.from(green) });
  const passed = page.getByRole("dialog", { name: "Checking green.html" });
  await expect(passed.getByText("It passes every check. A sample in it:").first()).toBeVisible();
  const checked = await (await page.request.post("/api/v1/templates/sections/check", { data: { html: green } })).json();
  await expectPageAccessible(page, checked.preview_html, "a template changed within the rules");
  await passed.getByRole("button", { name: "Use this template" }).click();
  await expect(page.getByText("Your template is in use.").first()).toBeVisible();
  await expect(resumes.getByText("Your template: green.html")).toBeVisible();

  // Back to the default, and Undo brings it back: no "Are you sure?" first.
  await resumes.getByRole("button", { name: /^Use the default\W+Resume$/ }).click();
  await expect(resumes.getByText("The default template")).toBeVisible();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(resumes.getByText("Your template: green.html")).toBeVisible();
  await page.request.delete("/api/v1/templates/sections");

  // Each default as a page of its own, as a reader opens it.
  for (const kind of ["sections", "letter"]) {
    const found = await (await page.request.get(`/api/v1/templates/${kind}`)).json();
    await expectPageAccessible(page, found.preview_html, `the default ${kind} template`);
  }
});
