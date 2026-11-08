import { expect, test } from "@playwright/test";

// Whatever happens here, registration is left open for the other journeys.
test.afterEach(async ({ page }) => {
  await page.request.put("/api/v1/system/registration", { data: { open: true } }).catch(() => undefined);
});

import { expectAccessible, signIn } from "./helpers";

const PASSWORD = "a long enough password";

/**
 * Someone makes their own account from the sign-in page and starts from nothing; the owner sees who has an
 * account (never what's in it), turns one off and on, closes registration, and deletes one.
 */
test("a new person registers into their own apply; the owner manages accounts in People", async ({ page }) => {
  const email = `sita-${Date.now() % 100000}@example.com`;
  await page.goto("/sign-in");
  await page.getByRole("link", { name: "Create an account" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Create an account" })).toBeVisible();
  await expect(page.getByText("Your own apply: your profiles, applications and documents, seen only by you.")).toBeVisible();
  await expectAccessible(page, "register, anyone");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("The password again").fill(PASSWORD);
  await page.getByRole("button", { name: "Create the account" }).click();
  await expect(page).toHaveURL(/\/profiles\/new/);

  // Their own: nothing of the owner's; the model is the owner's to choose; no People.
  await page.goto("/applications");
  await expect(page.getByText("0 applications").or(page.getByText(/No applications yet/)).first()).toBeVisible();
  await page.goto("/settings");
  await expect(page.getByText("The owner of this apply chooses the model; everyone here uses it.")).toBeVisible();
  await expect(page.getByRole("region", { name: "People" })).toHaveCount(0);

  // The owner: People lists them, with nothing of theirs.
  await page.context().clearCookies();
  await signIn(page);
  await page.goto("/settings");
  const people = page.getByRole("region", { name: "People" });
  const row = people.getByRole("listitem").filter({ hasText: email });
  await expect(row).toBeVisible();
  await expect(people.getByText("You (owner)")).toBeVisible();
  await expectAccessible(page, "settings: people");

  // Off: they can't sign in, and are told why. On again: they can.
  await row.getByRole("button", { name: new RegExp(`^Turn off\\W+${email}$`) }).click();
  await expect(row.getByText("Turned off")).toBeVisible();
  const visitor = await page.context().browser()!.newContext();
  const theirs = await visitor.newPage();
  await theirs.goto("http://127.0.0.1:3399/sign-in");
  await theirs.locator("#email").fill(email);
  await theirs.locator("#password").fill(PASSWORD);
  await theirs.locator("form button[type=submit]").click();
  await expect(theirs.getByText("This account is turned off. Ask the person who runs this apply.")).toBeVisible();
  await row.getByRole("button", { name: new RegExp(`^Turn on\\W+${email}$`) }).click();
  await expect(row.getByText("Turned off")).toHaveCount(0);

  // Registration closed: no "Create an account" for anyone; open again after.
  await people.getByRole("switch", { name: /Anyone can create an account/ }).uncheck();
  await theirs.goto("http://127.0.0.1:3399/sign-in");
  await expect(theirs.getByRole("heading", { level: 1, name: "Sign in" })).toBeVisible();
  await expect(theirs.getByRole("link", { name: "Create an account" })).toHaveCount(0);
  await people.getByRole("switch", { name: /Anyone can create an account/ }).check();
  await theirs.reload();
  await expect(theirs.getByRole("link", { name: "Create an account" })).toBeVisible();
  await visitor.close();

  // Deleting is asked first: it can't be undone.
  await row.getByRole("button", { name: new RegExp(`^Delete\\W+${email}$`) }).click();
  const confirm = page.getByRole("alertdialog", { name: `Delete ${email}'s account?` });
  await expectAccessible(page, "settings: delete an account");
  await confirm.getByRole("button", { name: "Delete" }).click();
  await expect(people.getByText(email)).toHaveCount(0);
});

test("asked for at sign-up, the demo puts John Doe's applications in the new account", async ({ page }) => {
  const email = `demo-${Date.now() % 100000}@example.com`;
  await page.goto("/register");
  const sample = page.getByRole("checkbox", { name: "Add a sample profile to look around" });
  await expect(sample).not.toBeChecked(); // never unless asked
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("The password again").fill(PASSWORD);
  await sample.check();
  await expectAccessible(page, "register, with the demo");
  await page.getByRole("button", { name: "Create the account" }).click();
  await expect(page).toHaveURL(/\/applications/);
  await expect(page.getByText("Senior Lorem Engineer").first()).toBeVisible();
  await expect(page.getByText("3 applications").first()).toBeVisible();
});
