import { expect, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";

test("Settings → Model finds the models here, tests one, uses it, and goes back to the settings'", async ({ page }) => {
  await signIn(page);
  await page.goto("/settings");
  const section = page.getByRole("region", { name: "Model" });
  await expect(section.getByText("In use: writer:8b on 127.0.0.1")).toBeVisible();
  await expect(section.getByText("From the settings (.env).")).toBeVisible();

  // What the fake model server has: the one in use (loaded), a bigger one, and an embedding model that can't be chosen.
  const model = section.getByLabel("Model", { exact: true });
  await expect(model.locator("optgroup")).toHaveAttribute("label", /^Model server · 127\.0\.0\.1:\d+$/);
  await expect(model.locator("option")).toHaveText([
    "writer:8b · 8.2B · 5.2 GB · loaded",
    "writer:14b · 8.2B · 5.2 GB",
    "embedder:latest · 8.2B · 5.2 GB · embeddings only",
  ]);
  await expect(model.locator("option").nth(2)).toBeDisabled();
  const about = section.getByRole("definition").filter({ hasText: "Loaded now" });
  await expect(about).toBeVisible();
  await expectAccessible(page, "settings: model");

  await model.selectOption({ label: "writer:14b · 8.2B · 5.2 GB" });
  await expect(section.getByText("Loads on first use")).toBeVisible();
  await section.getByLabel("Writing model").selectOption({ label: "The same model" });
  await section.getByRole("button", { name: "Test and use" }).click();
  await expect(page.getByText(/^Now using writer:14b\. It answered in [\d.]+ s\.$/)).toBeVisible();
  await expect(section.getByText("In use: writer:14b on 127.0.0.1")).toBeVisible();
  await expect(section.getByText("Chosen here.")).toBeVisible();

  // Remembered: a new page load says the same.
  await page.reload();
  await expect(page.getByRole("region", { name: "Model" }).getByText("In use: writer:14b on 127.0.0.1")).toBeVisible();

  await page.getByRole("region", { name: "Model" }).getByRole("button", { name: "Use the settings (.env)" }).click();
  await expect(page.getByText("Back to the model in the settings.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Model" }).getByText("In use: writer:8b on 127.0.0.1")).toBeVisible();
});
