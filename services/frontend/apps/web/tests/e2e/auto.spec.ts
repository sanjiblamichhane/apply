/**
 * Auto on the web: a search with Auto on prepares a strong match (tracked, documents written and checked) and it's
 * Ready for you, with the board's form to open; apply never sends it. The person's submission makes it sent.
 * A second one to the same employer needs you (the reason, Dismiss), and Pause Auto.
 */
import { expect, type Page, test } from "@playwright/test";

import { expectAccessible, signIn } from "./helpers";

const FORM = (slug: string) => `https://jobs.ashbyhq.com/${slug}/f3e1c2b4-1111-4111-8111-111111111111/application`;

async function posting(page: Page, title: string, issuer: string, slug: string) {
  const opp = await (await page.request.post("/api/v1/opportunities", { data: { text: `${title} at ${issuer}\nPython and Django.` } })).json();
  await expect.poll(async () => (await (await page.request.get(`/api/v1/opportunities/${opp.id}`)).json()).extraction.status).not.toBe("pending");
  await page.request.patch(`/api/v1/opportunities/${opp.id}`, { data: { title, issuer_name: issuer, apply_url: FORM(slug) } });
}

test("a search with Auto on: prepared, Ready for you, sent by the person; the same employer needs you; Pause Auto", async ({ page }) => {
  test.setTimeout(180_000);
  await signIn(page);
  // Its own profile (not the default: other journeys write from theirs), chosen in the search, removed after.
  const profile = await (await page.request.post("/api/v1/profiles", { data: {
    pack: "job", kind: "individual", name: "Auto profile", summary: "", is_default: false,
    attributes: { full_name: "Sam Rai", email: "sam@example.com",
      experience: [{ title: "Backend Engineer", organisation: "Himal Tech", highlights: ["Led a team of 12 engineers"] }] },
  } })).json();
  try {
    await autoJourney(page);
  } finally {
    // Leave nothing behind for the other journeys: the search, and the profile (the default, if it was first).
    const searches = (await (await page.request.get("/api/v1/searches")).json()).items as { id: string; name: string }[];
    for (const s of searches.filter((x) => x.name.startsWith("Zeta"))) await page.request.delete(`/api/v1/searches/${s.id}`);
    await page.request.delete(`/api/v1/profiles/${profile.id}`);
    await page.request.patch("/api/v1/auto/settings", { data: { auto_paused: false } });
  }
});

async function autoJourney(page: Page) {
  await posting(page, "Zeta Backend Engineer", "Zeta Robotics", "zeta");

  await page.goto("/searches/new");
  await page.getByLabel("Name", { exact: true }).fill("Zeta, prepared");
  await page.getByLabel("Words to look for", { exact: true }).fill("zeta");
  await page.getByLabel("Score against").selectOption({ label: "Auto profile" });
  await page.getByLabel("Prepare strong matches").check();
  await page.locator("form button[type=submit]").click();
  await expect(page).toHaveURL(/\/searches$/);

  // Ready for you: the documents written and checked, the board's form to open. Nothing was sent.
  await page.goto("/ready");
  const card = page.getByRole("listitem").filter({ hasText: "Zeta Backend Engineer" });
  await expect(card.getByText("Ready for you", { exact: true })).toBeVisible({ timeout: 90_000 });
  await expect(card.getByText("Open the form: the extension fills it from your profile, then you check it and press Submit.")).toBeVisible();
  const form = card.getByRole("link", { name: /^Open the form\s*: Zeta Backend Engineer \(opens in a new tab\)$/ });
  await expect(form).toHaveAttribute("href", FORM("zeta"));
  await expect(form).toHaveAttribute("target", "_blank");
  await expect(form).toHaveAttribute("rel", /noopener/);
  await expect(card.getByRole("button", { name: /Send/ })).toHaveCount(0);
  await expect(page.getByRole("navigation").getByRole("link", { name: /Ready for you 1/ })).toBeVisible();
  await expectAccessible(page, "ready for you");

  // The person sends it (the extension records it; here, "I've submitted it" through the API): it's sent.
  const run = (await (await page.request.get("/api/v1/auto/runs?group=ready")).json()).items
    .find((r: { opportunity: { title: string } }) => r.opportunity.title === "Zeta Backend Engineer");
  const kit = await (await page.request.get(`/api/v1/applications/${run.application_id}/kit`)).json();
  expect(kit.submissions).toEqual([]);
  expect((await page.request.post(`/api/v1/applications/${run.application_id}/submissions`, { data: {} })).ok()).toBe(true);
  await page.reload();
  const sent = page.getByRole("region", { name: "Sent recently" });
  await expect(sent.getByRole("heading", { name: "Zeta Backend Engineer" })).toBeVisible({ timeout: 20_000 });

  // A second one at the same employer: Needs you, with the reason, then Dismiss.
  await posting(page, "Zeta Platform Engineer", "Zeta Robotics, Inc.", "zetainc");
  const search = (await (await page.request.get("/api/v1/searches")).json()).items.find((s: { name: string }) => s.name === "Zeta, prepared");
  await page.request.patch(`/api/v1/searches/${search.id}`, { data: { name: "Zeta, prepared!" } });
  await page.goto("/needs-you");
  const blocked = page.getByRole("listitem").filter({ hasText: "Zeta Platform Engineer" });
  await expect(blocked.getByText("You've applied to this employer in the last 30 days, so apply leaves this one to you."))
    .toBeVisible({ timeout: 60_000 });
  await expectAccessible(page, "needs you");
  await blocked.getByRole("button", { name: "Dismiss" }).click();
  await expect(page.getByText("Nothing needs you.")).toBeVisible();

  // Pause Auto: one switch, and it says so.
  const pause = page.getByRole("switch", { name: "Pause Auto" });
  await pause.click();
  await expect(pause).toHaveAttribute("aria-checked", "true");
  await expect(page.getByText(/Auto is paused/)).toBeVisible();
  await page.goto("/settings");
  const settings = page.getByRole("region", { name: "Auto" });
  await expect(settings.getByRole("switch", { name: "Pause Auto" })).toHaveAttribute("aria-checked", "true");
  await expect(settings.getByLabel(/hours/)).toHaveCount(0); // no hold: nothing is sent for you
  await settings.getByRole("switch", { name: "Pause Auto" }).click();
  await expect(settings.getByRole("switch", { name: "Pause Auto" })).toHaveAttribute("aria-checked", "false");
  await expectAccessible(page, "settings: Auto");
}

test("Auto's screens in Nepali, and the old address", async ({ page }) => {
  await signIn(page, "ne");
  await page.goto("/waiting"); // "Waiting to send" is now Ready for you
  await expect(page).toHaveURL(/\/ready$/);
  await expect(page.getByRole("heading", { level: 1, name: "तपाईंका लागि तयार" })).toBeVisible();
  await expectAccessible(page, "ready for you, Nepali");
  await page.goto("/needs-you");
  await expect(page.getByRole("heading", { level: 1, name: "तपाईं चाहिएको" })).toBeVisible();
  await expect(page.getByRole("switch", { name: "स्वचालित रोक्नुहोस्" })).toBeVisible();
  await expectAccessible(page, "needs you, Nepali");
});
