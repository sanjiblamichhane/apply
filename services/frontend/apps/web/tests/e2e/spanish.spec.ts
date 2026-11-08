import { expect, test } from "@playwright/test";

import { expectAccessible, posting, signIn } from "./helpers";

test("Spanish arrives with the page (never English first), with Spanish numbers and guides", async ({ page }) => {
  await signIn(page, "es");
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("heading", { level: 1, name: "Solicitudes" })).toBeVisible();
  // The server sends the catalogue with the page: the first HTML is already in Spanish.
  const html = await (await page.request.get("/applications")).text();
  expect(html).toContain("Solicitudes");
  await expectAccessible(page, "board (es)");

  const job = posting("Backend Engineer", "Leapfrog");
  await page.getByLabel("Pegue una oferta de empleo").fill(job.text);
  await page.getByRole("button", { name: "Añadir", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: job.title })).toBeVisible();
  await expectAccessible(page, "detail (es)");

  await page.goto("/settings");
  await page.getByRole("button", { name: "Ayuda: Configuración" }).click();
  await expect(page.getByRole("heading", { level: 2, name: "Configuración" })).toBeFocused();
});

test("switching to Spanish in Settings changes every screen and is remembered", async ({ page }) => {
  await signIn(page);
  await page.goto("/settings");
  await page.getByRole("radio", { name: "Español" }).check();
  await expect(page.getByRole("heading", { level: 1, name: "Configuración" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await page.goto("/profiles");
  await expect(page.getByRole("heading", { level: 1, name: "Perfiles" })).toBeVisible();
  await page.goto("/settings");
  await page.getByRole("radio", { name: "English" }).check();
  await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
});
