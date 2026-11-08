import { expect, type APIRequestContext, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

const OLD = "the first long password";
const NEW = "a second long password";

/** The newest email the mail catcher has for this address (the suite's own: nothing is really sent). */
async function linkSentTo(request: APIRequestContext, email: string): Promise<string> {
  const mail = process.env.APPLY_E2E_MAIL_URL!;
  let found = "";
  await expect.poll(async () => {
    const search = await (await request.get(`${mail}/api/v1/search`, { params: { query: `to:"${email}"` } })).json();
    const id = search.messages?.[0]?.ID;
    if (!id) return "";
    const message = await (await request.get(`${mail}/api/v1/message/${id}`)).json();
    found = message.Text.match(/http:\/\/127\.0\.0\.1:3399\/reset-password\?token=[\w-]+/)?.[0] ?? "";
    return found;
  }, { message: `an email to ${email}`, timeout: 15_000 }).not.toBe("");
  return found;
}

/**
 * Forgot your password: a link by email (caught by the local mail catcher), a new password, signed out everywhere, and the
 * link used up. An email with no account gets the same answer and no email.
 */
test("a forgotten password is reset from an emailed link", async ({ page, browser }) => {
  const email = `maya-${Date.now() % 100000}@example.com`;
  expect((await page.request.post("/api/v1/auth/register", { data: { email, password: OLD } })).ok()).toBe(true);
  // Signed in elsewhere too: that session ends with the new password.
  const elsewhere = await browser.newContext({ baseURL: "http://127.0.0.1:3399" });
  expect((await elsewhere.request.post("/api/v1/auth/sign-in", { data: { email, password: OLD } })).ok()).toBe(true);
  await page.context().clearCookies();

  await page.goto("/sign-in");
  await page.getByRole("link", { name: "Forgot your password?" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Forgot your password?" })).toBeVisible();
  await expectAccessible(page, "forgot password");

  // No such account: the same words, and nothing sent.
  await page.getByLabel("Email").fill("nobody-here@example.com");
  await page.getByRole("button", { name: "Send the link" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Check your email" })).toBeVisible();
  await expect(page.getByText("If there's an account for nobody-here@example.com, we've sent it a link.", { exact: false })).toBeVisible();

  await page.goto("/forgot-password");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Send the link" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Check your email" })).toBeVisible();
  await expectAccessible(page, "forgot password, sent");
  const link = await linkSentTo(page.request, email);
  const none = await (await page.request.get(`${process.env.APPLY_E2E_MAIL_URL}/api/v1/search`,
    { params: { query: 'to:"nobody-here@example.com"' } })).json();
  expect(none.messages_count ?? none.messages.length).toBe(0);

  // The link: the token is taken out of the address at once.
  await page.goto(link);
  await expect(page.getByRole("heading", { level: 1, name: "Choose a new password" })).toBeVisible();
  await expect(page).toHaveURL(/\/reset-password$/);
  await expect(page.getByText(`For ${email}.`, { exact: false })).toBeVisible();
  await expectAccessible(page, "reset password");
  await page.getByLabel("New password", { exact: true }).fill("too short");
  await page.getByLabel("The password again").fill("too short");
  await page.getByRole("button", { name: "Change the password" }).click();
  await expect(page.getByLabel("New password", { exact: true })).toHaveAttribute("aria-invalid", "true");
  await page.getByLabel("New password", { exact: true }).fill(NEW);
  await page.getByLabel("The password again").fill(NEW);
  await page.getByRole("button", { name: "Change the password" }).click();

  await expect(page).toHaveURL(/\/sign-in\?reset=done/);
  await expect(page.getByRole("status").filter({ hasText: "Your password is changed. Sign in with the new one." })).toBeVisible();
  await expectAccessible(page, "sign in after a reset");
  expect((await elsewhere.request.get("/api/v1/auth/me")).status()).toBe(401);
  await elsewhere.close();

  await page.locator("#email").fill(email);
  await page.locator("#password").fill(NEW);
  await page.locator("form button[type=submit]").click();
  await expect(page).toHaveURL(/\/today|\/profiles/);

  // Used once: the link now says so, and offers a new one.
  await page.context().clearCookies();
  await page.goto(link);
  await expect(page.getByRole("heading", { level: 1, name: "This link doesn't work any more" })).toBeVisible();
  await expectAccessible(page, "reset link used");
  await page.getByRole("link", { name: "Send a new link" }).click();
  await expect(page).toHaveURL(/\/forgot-password/);
});
