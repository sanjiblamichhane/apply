/**
 * The extension's journeys: on each of the three boards the extension fills the form, the person presses
 * Submit, and apply records it and moves the application along by itself.
 */
import { connect, expect, expectAccessible, openPanel, PROFILE, received, setup, test } from "./fixtures";

test.beforeAll(async () => {
  // One profile for the run (the owner's default), set up through the API.
  const { Apply } = await import("./fixtures");
  const { ownerSession } = await import("@apply/e2e-harness");
  const apply = new Apply(await ownerSession(setup.apiUrl));
  const profiles = await apply.call<{ items: unknown[] }>("GET", "/api/v1/profiles");
  if (profiles.items.length === 0) await apply.call("POST", "/api/v1/profiles", PROFILE);
  await apply.call("POST", "/api/v1/answers/defaults");
  const answers = await apply.call<{ items: { id: string; key: string }[] }>("GET", "/api/v1/answers");
  const set = async (key: string, answer: string) =>
    apply.call("PATCH", `/api/v1/answers/${answers.items.find((a) => a.key === key)!.id}`, { answer });
  await set("work_authorization", "yes");
  await set("needs_sponsorship", "no");
  await set("notice_period", "One month");
  await set("relocate", "yes");
  await set("heard_from", "apply");
});

test("board01: track the job from its form, fill it, submit, recorded, undo", async ({ context, extensionId, apply, token }) => {
  const board = await context.newPage();
  await board.goto(setup.boards.board01);
  const panel = await openPanel(context, extensionId, board);
  await connect(panel, token);
  await expectAccessible(panel, "panel: not tracked yet");

  await expect(panel.getByText("Not tracked in apply yet")).toBeVisible();
  await panel.getByRole("button", { name: "Track this job" }).click();
  await expect(panel.getByRole("heading", { name: "Senior Backend Engineer" })).toBeVisible();
  await expect(panel.getByText(/No documents yet/)).toBeVisible();

  const found = await apply.call<{ application: { id: string } }>("GET",
    `/api/v1/applications/by-url?url=${encodeURIComponent(setup.boards.board01)}`);
  await apply.writeDocuments(found.application.id);
  await panel.reload();
  await expect(panel.getByText("Resume", { exact: true })).toBeVisible();
  await expect(panel.getByText("Not reviewed yet").first()).toBeVisible();

  // First, what would go where, with nothing written yet; the person unticks one and confirms.
  await expect(panel.getByRole("heading", { name: "apply will fill (14)" })).toBeVisible();
  await expect(panel.getByRole("checkbox", { name: /^First Name/ })).toBeChecked();
  await expect(panel.getByText("sam@example.com")).toBeVisible();
  await expect(panel.getByText("Sam Rai – Resume.pdf")).toBeVisible();
  await expect(panel.getByText("Hidden: an equal-opportunity answer").first()).toBeVisible();
  await expect(board.locator("#first_name")).toHaveValue("");
  await expectAccessible(panel, "panel: before filling");
  // Check the form again: an answer changed in apply since shows in the list, without reloading anything.
  const answers = await apply.call<{ items: { id: string; key: string }[] }>("GET", "/api/v1/answers");
  const heard = answers.items.find((a) => a.key === "heard_from")!.id;
  await apply.call("PATCH", `/api/v1/answers/${heard}`, { answer: "A friend" });
  await panel.getByRole("button", { name: "Check the form again" }).click();
  await expect(panel.getByText("A friend", { exact: true })).toBeVisible();
  await expect(panel.getByRole("status").filter({ hasText: "Checked the form again" })).toBeAttached();
  await apply.call("PATCH", `/api/v1/answers/${heard}`, { answer: "apply" });
  await panel.getByRole("button", { name: "Check the form again" }).click();
  await expect(panel.getByText("A friend", { exact: true })).toHaveCount(0);
  await panel.getByRole("checkbox", { name: /^How did you hear about this job\?/ }).uncheck();
  await expect(panel.getByRole("heading", { name: "apply will fill (13)" })).toBeVisible();
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText("Filled 11 fields")).toBeVisible();
  await expect(panel.getByText("Attached: Resume, Cover letter")).toBeVisible();
  await expect(panel.getByRole("heading", { name: /^apply will fill/ })).toHaveCount(0);
  const left = panel.getByRole("list").last();
  await expect(left.getByText("Why do you want to work at Acme Robotics?")).toBeVisible();
  await expect(left.getByText("agreeing is yours to do")).toBeVisible();
  await expect(left.getByText("you chose to fill it in yourself")).toBeVisible();
  await expect(board.locator("#question_31337006")).toHaveValue("");
  await expectAccessible(panel, "panel: filled");

  // On the board's own page: what a person would see before pressing Submit.
  await expect(board.locator("#first_name")).toHaveValue("Sam");
  await expect(board.locator("#email")).toHaveValue("sam@example.com");
  await expect(board.locator("#question_31337003 option:checked")).toHaveText("Yes");
  await expect(board.locator("#gender option:checked")).toHaveText("Decline To Self Identify");
  await expect(board.locator("#gdpr_consent")).not.toBeChecked();
  expect(await board.locator("#resume").evaluate((el: HTMLInputElement) => el.files?.[0]?.name)).toBe("Sam Rai – Resume.pdf");

  // The person answers what was left, agrees, and presses Submit themselves.
  await board.locator("#question_31337005").fill("I like robots.");
  await board.locator("#gdpr_consent").check();
  await board.getByRole("button", { name: "Submit application" }).click();
  await expect(board.getByRole("heading", { name: "Thank you for applying." })).toBeVisible();

  await expect(panel.getByRole("heading", { name: "Recorded as submitted" })).toBeVisible();
  await expect(panel.getByText("Moved to In progress")).toBeVisible();
  const app = await apply.call<{ stage: { code: string } }>("GET", `/api/v1/applications/${found.application.id}`);
  expect(app.stage.code).toBe("in_progress");
  const kit = await apply.call<{ submissions: { channel: string; details: { filled: { fields: number; files: string[] } } }[] }>(
    "GET", `/api/v1/applications/${found.application.id}/kit`);
  expect(kit.submissions[0]).toMatchObject({ channel: "extension", details: { filled: { fields: 11, files: ["resume", "cover_letter"] } } });

  const [sent] = await received("board01");
  expect(sent!.fields).toMatchObject({ first_name: "Sam", last_name: "Rai", email: "sam@example.com", question_31337003: "1", question_31337004: "0" });
  expect(sent!.files.find((f) => f.field === "resume")).toMatchObject({ filename: "Sam Rai – Resume.pdf", head: "%PDF-" });

  await panel.getByRole("button", { name: "Undo" }).click();
  await expect(panel.getByRole("heading", { name: /Undone/ })).toBeVisible();
  const back = await apply.call<{ stage: { code: string } }>("GET", `/api/v1/applications/${found.application.id}`);
  expect(back.stage.code).toBe("new");
});

test("board02: radios, links and cards; the thank-you page after a redirect", async ({ context, extensionId, apply, token }) => {
  const opp = await apply.call<{ id: string }>("POST", "/api/v1/opportunities", { url: setup.boards.board02 });
  const app = await apply.call<{ id: string }>("POST", "/api/v1/applications", { opportunity_id: opp.id });
  await apply.writeDocuments(app.id);

  const board = await context.newPage();
  await board.goto(setup.boards.board02);
  const panel = await openPanel(context, extensionId, board);
  await connect(panel, token);
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText(/^Filled \d+ fields$/)).toBeVisible();
  await expect(board.locator('[name="name"]')).toHaveValue("Sam Rai");
  await expect(board.locator('[name="urls[LinkedIn]"]')).toHaveValue("https://www.linkedin.com/in/example");
  await expect(board.locator('[name="cards[0b1c][field0]"]')).toHaveValue("One month");
  await expect(board.locator('input[name="cards[0b1c][field1]"][value="Yes"]')).toBeChecked();

  await board.getByRole("button", { name: "Submit application" }).click();
  await expect(board.getByRole("heading", { name: "Application submitted!" })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Recorded as submitted" })).toBeVisible();
  const [sent] = await received("board02");
  expect(sent!.fields).toMatchObject({ name: "Sam Rai", org: "Himal Tech", "cards[0b1c][field1]": "Yes", "eeo[gender]": "Decline to self-identify" });
  expect(sent!.files[0]).toMatchObject({ field: "resume", head: "%PDF-" });
});

test("board03: a form drawn by script, filled the way its own code notices, thanked in place", async ({ context, extensionId, apply, token }) => {
  const opp = await apply.call<{ id: string }>("POST", "/api/v1/opportunities", { url: setup.boards.board03 });
  const app = await apply.call<{ id: string }>("POST", "/api/v1/applications", { opportunity_id: opp.id });
  await apply.writeDocuments(app.id);

  const board = await context.newPage();
  await board.goto(setup.boards.board03);
  const panel = await openPanel(context, extensionId, board);
  await connect(panel, token);
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText(/^Filled \d+ fields$/)).toBeVisible();
  await expect(panel.getByText("Why Example Analytics?")).toBeVisible(); // its essay question: left for you
  await expect(board.getByRole("button", { name: "No", pressed: true })).toBeVisible(); // its own Yes / No buttons

  await board.getByRole("button", { name: "Submit Application" }).click();
  await expect(board.getByRole("heading", { name: "Thank you for applying!" })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Recorded as submitted" })).toBeVisible();
  const [sent] = await received("board03");
  // Only values that arrived with the page's input events are sent: so these were filled as a person would.
  expect(sent!.fields).toMatchObject({
    _systemfield_name: "Sam Rai", _systemfield_email: "sam@example.com", "7c3d-notice": "One month",
    "eeo:I prefer not to answer": "true", // the sensitive answer, declined on the board's own option
    "choice:Will you require visa sponsorship?": "No",
  });
  expect(sent!.fields["eeo:White"]).toBeUndefined();
  expect(sent!.files[0]).toMatchObject({ field: "_systemfield_resume", filename: "Sam Rai – Resume.pdf" });
});

test("in Nepali, and away from a board", async ({ context, extensionId, token }) => {
  const panel = await openPanel(context, extensionId);
  await panel.getByLabel("Language").selectOption("ne");
  await expect(panel.getByRole("heading", { name: "apply सँग जोड्नुहोस्" })).toBeVisible();
  await expectAccessible(panel, "panel: connect, Nepali");
  await connect(panel, token);
  await expect(panel.getByRole("heading", { name: "आवेदन फारम खोल्नुहोस्" })).toBeVisible();
  await expectAccessible(panel, "panel: not a board, Nepali");

  const bad = await openPanel(context, extensionId);
  await bad.getByRole("button", { name: "सेटिङ" }).click();
  await expect(bad.getByRole("button", { name: "पछाडि" })).toBeFocused();
  await expect(bad.getByText("owner@example.com को रूपमा जोडिएको")).toBeVisible();
  await expectAccessible(bad, "panel: settings, Nepali");
  await bad.getByRole("button", { name: "छुटाउनुहोस्" }).click();
  await bad.locator("#token").fill("apl_not_a_real_token_at_all_0000000000000");
  await bad.getByRole("button", { name: "जोड्नुहोस्" }).click();
  await expect(bad.getByRole("alert")).toContainText("टोकनले काम गर्दैन");
});

test("a careers site apply doesn't know: tracked, filled by its labels, consent left, recorded", async ({ context, extensionId, apply, token }) => {
  const site = await context.newPage();
  await site.goto(setup.boards.other);
  const panel = await openPanel(context, extensionId, site);
  await connect(panel, token);

  await expect(panel.getByText("Not tracked in apply yet")).toBeVisible();
  await panel.getByRole("button", { name: "Track this job" }).click();
  await expect(panel.getByRole("heading", { name: "Platform Engineer", exact: true })).toBeVisible();
  await expect(panel.getByText(/No documents yet/)).toBeVisible();
  const found = await apply.call<{ application: { id: string } }>("GET",
    `/api/v1/applications/by-url?url=${encodeURIComponent(setup.boards.other.replace(/\/apply$/, ""))}`); // the posting's own address
  await apply.writeDocuments(found.application.id);
  await panel.reload();

  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText(/^Filled \d+ fields$/)).toBeVisible();
  await expect(panel.getByText("Attached: Resume")).toBeVisible();
  const left = panel.getByRole("list").last();
  await expect(left.getByText("Why do you want to join Yeti Cloud?")).toBeVisible();
  await expect(left.getByText("agreeing is yours to do")).toBeVisible();
  const host = new URL(setup.boards.other).host;
  await expect(panel.getByRole("button", { name: `Stop using apply on ${host}` })).toBeVisible();
  await expectAccessible(panel, "panel: filled on another site");

  // The search box at the top is left alone: only the application form is filled.
  await expect(site.getByLabel("Search jobs")).toHaveValue("");
  await expect(site.locator("#given")).toHaveValue("Sam");
  await expect(site.locator("#family")).toHaveValue("Rai");
  await expect(site.locator("#mail")).toHaveValue("sam@example.com");
  await expect(site.locator("#li")).toHaveValue("https://www.linkedin.com/in/example");
  await expect(site.locator("input[name=privacy]")).not.toBeChecked();

  await site.locator("#why").fill("Platforms are my thing.");
  await site.locator("input[name=privacy]").check();
  await site.getByRole("button", { name: "Send application" }).click();
  await expect(site.getByRole("heading", { name: "Thank you for applying!" })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Recorded as submitted" })).toBeVisible();

  const [sent] = await received("other");
  expect(sent!.fields).toMatchObject({ given: "Sam", family: "Rai", mail: "sam@example.com" });
  expect(sent!.files.find((f) => f.field === "cv")).toMatchObject({ filename: "Sam Rai – Resume.pdf", head: "%PDF-" });
});

test("board04: its job page, signing in, then each step filled as it's drawn at the same address", async ({ context, extensionId, apply, token }) => {
  const site = await context.newPage();
  await site.goto(setup.boards.board04);
  const panel = await openPanel(context, extensionId, site);
  await connect(panel, token);

  // The job page: press Apply. Then board04's sign-in: the person's to do.
  await expect(panel.getByText(/This is the job.s page\. Press Apply/)).toBeVisible();
  await site.getByRole("button", { name: "Apply" }).click();
  await expect(panel.getByRole("heading", { name: "Sign in to this site" })).toBeVisible();
  await expectAccessible(panel, "panel: sign in to board04");
  await site.getByRole("button", { name: "Sign In" }).click();

  // My Information, drawn in place: the panel notices without a page load.
  await expect(panel.getByText("Not tracked in apply yet")).toBeVisible();
  await panel.getByRole("button", { name: "Track this job" }).click();
  await expect(panel.getByText(/No documents yet/)).toBeVisible();
  const found = await apply.call<{ application: { id: string } }>("GET",
    `/api/v1/applications/by-url?url=${encodeURIComponent(setup.boards.board04)}`); // the job page's address
  await apply.writeDocuments(found.application.id);
  await panel.reload();

  await expect(panel.getByText(/This form comes in steps/)).toBeVisible();
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText(/^Filled \d+ fields$/)).toBeVisible();
  const left = panel.getByRole("list").last();
  await expect(left.getByText("How Did You Hear About Us?")).toBeVisible();
  await expect(site.getByLabel("First Name")).toHaveValue("Sam");
  await expect(site.getByLabel("Last Name")).toHaveValue("Rai");
  await expect(site.getByLabel("Phone Number")).toHaveValue("+977 980 000 0000");
  // Its own dropdowns are never opened or pressed: the person chooses, and the panel says what to choose.
  // Himal Tech is in the profile, so "worked there before" is Yes.
  await expect(site.locator("[data-automation-id=previousWorker]")).toHaveText("Select One");
  await expect(site.locator("[data-automation-id=wd-popup]")).toHaveCount(0);
  await expect(left.getByRole("listitem").filter({ hasText: "Have you ever previously been employed" })
    .getByText("Your answer: Yes")).toBeVisible();
  await expectAccessible(panel, "panel: board04's first step filled");

  // The person presses Save and Continue; the next step is drawn, and the panel starts it afresh.
  await site.getByRole("button", { name: "Save and Continue" }).click();
  await expect(panel.getByRole("button", { name: "Fill the form" })).toBeVisible();
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText("Attached: Resume")).toBeVisible();
  await expect(site.getByLabel("LinkedIn")).toHaveValue("https://www.linkedin.com/in/example");

  await site.getByRole("button", { name: "Submit" }).click();
  await expect(site.getByRole("heading", { name: "Thank you for applying!" })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Recorded as submitted" })).toBeVisible();
  const [sent] = await received("board04");
  expect(sent!.fields).toMatchObject({ legalNameSection_firstName: "Sam", legalNameSection_lastName: "Rai", email: "sam@example.com" });
  expect(sent!.files.find((f) => f.field === "file-upload-input-ref")).toMatchObject({ filename: "Sam Rai – Resume.pdf", head: "%PDF-" });
});

test("Copy: the profile beside any page; a click puts a value on the clipboard, cleared a minute later if asked", async ({ context, extensionId, apply, token }) => {
  // A second profile, to switch to with the chips.
  const profiles = await apply.call<{ items: { name: string }[] }>("GET", "/api/v1/profiles");
  if (!profiles.items.some((p) => p.name === "Second profile")) {
    await apply.call("POST", "/api/v1/profiles", { ...PROFILE, name: "Second profile", is_default: false, attributes: { ...PROFILE.attributes, email: "second@example.com" } });
  }
  const panel = await openPanel(context, extensionId);
  await connect(panel, token, "copy");
  const clipboard = () => panel.evaluate(() => navigator.clipboard.readText());
  const row = (label: string) => panel.getByRole("button").filter({ hasText: label });
  const searchBox = panel.getByRole("searchbox", { name: "Search your profile" });

  for (const name of ["Basics", "Experience", "More", "Answers"]) await expect(panel.getByRole("tab", { name })).toBeVisible();
  // One row at the top: the profile, then every tool as a named icon.
  for (const name of ["Search your profile", "Refresh", "Settings"]) await expect(panel.getByRole("button", { name })).toBeVisible();
  // Each icon names itself in a tooltip on hover (the browser's side panel doesn't show native title tooltips).
  for (const [role, name] of [["button", "Refresh"], ["tab", "Fill"], ["button", "Settings"]] as const) {
    await panel.getByRole(role, { name, exact: true }).hover();
    await expect(panel.getByRole("tooltip", { name })).toBeVisible();
    // Off it, then once more, as a hand would: it stays open while the pointer could be heading into it.
    await panel.mouse.move(0, 400);
    await panel.mouse.move(0, 600, { steps: 4 });
  }
  for (const name of ["Copy", "Fill"]) await expect(panel.getByRole("tab", { name })).toBeVisible();
  await expectAccessible(panel, "panel: copy");

  await row("sam@example.com").click();
  await expect(panel.getByRole("status").filter({ hasText: "Copied: Email" })).toBeAttached();
  await expect(row("sam@example.com")).toContainText("Copied");
  expect(await clipboard()).toBe("sam@example.com");
  await row("First name").click();
  expect(await clipboard()).toBe("Sam");

  // Profiles are chips: one tap, and the other profile's values show.
  // The profile is one choice from a searchable list: type to narrow it, Enter to choose; or click one.
  await panel.getByRole("button", { name: `Profile: ${PROFILE.name}` }).click();
  const find = panel.getByRole("combobox", { name: "Find a profile" });
  await expect(find).toBeFocused();
  await expect(panel.getByRole("option", { name: PROFILE.name, selected: true })).toBeVisible();
  await expectAccessible(panel, "panel: copy, choosing a profile");
  await find.fill("second");
  await expect(panel.getByRole("option")).toHaveCount(1);
  await find.press("Enter");
  await expect(panel.getByRole("button", { name: "Profile: Second profile" })).toBeFocused();
  await row("second@example.com").click();
  expect(await clipboard()).toBe("second@example.com");
  await panel.getByRole("button", { name: "Profile: Second profile" }).click();
  await panel.getByRole("option", { name: PROFILE.name }).click();
  await expect(panel.getByRole("button", { name: `Profile: ${PROFILE.name}` })).toBeVisible();
  await expect(row("sam@example.com")).toBeVisible();

  // The tabs by keyboard: the next one with →. Each job folds to a line; the first starts open.
  await panel.getByRole("tab", { name: "Basics" }).focus();
  await panel.keyboard.press("ArrowRight");
  await expect(panel.getByRole("tab", { name: "Experience", selected: true })).toBeFocused();
  const job = panel.getByRole("button", { name: "Backend Engineer, Himal Tech" });
  await expect(job).toHaveAttribute("aria-expanded", "true");
  await job.click();
  await expect(job).toHaveAttribute("aria-expanded", "false");
  await job.click();
  await expectAccessible(panel, "panel: copy, experience");

  // One search across every tab, behind its icon (or "/"); Enter copies the first match, Escape clears, then closes.
  await panel.getByRole("button", { name: "Search your profile" }).click();
  await expect(searchBox).toBeFocused();
  await searchBox.press("Escape");
  await expect(searchBox).toHaveCount(0);
  await panel.keyboard.press("/");
  await expect(searchBox).toBeFocused();
  await searchBox.fill("notice");
  await searchBox.press("Enter");
  expect(await clipboard()).toBe("One month");
  await searchBox.press("Escape");
  await expect(searchBox).toHaveValue("");

  // An equal-opportunity answer stays hidden until asked for.
  await panel.getByRole("tab", { name: "Answers" }).click();
  await expect(panel.getByText("Hidden: an equal-opportunity answer. Show it to copy it.").first()).toBeVisible();
  await expectAccessible(panel, "panel: copy, answers");

  // Cleared a minute later (the test build: 1.5 s), but only what apply copied. The setting is in Settings.
  await panel.getByRole("button", { name: "Settings" }).click();
  await expect(panel.getByText(/Click a value to copy it, then paste it into the form with (Ctrl\+V|⌘V)\./)).toBeVisible();
  await panel.getByLabel("Clear the clipboard a minute after copying").check();
  await expectAccessible(panel, "panel: settings");
  await panel.getByRole("button", { name: "Back" }).click();
  await expect(panel.getByRole("button", { name: "Settings" })).toBeFocused();
  await panel.getByRole("tab", { name: "Basics" }).click();
  await row("sam@example.com").click();
  expect(await clipboard()).toBe("sam@example.com");
  await expect.poll(clipboard, { timeout: 10_000 }).toBe("");
  await row("sam@example.com").click();
  await panel.evaluate(() => navigator.clipboard.writeText("something the person copied since"));
  await panel.waitForTimeout(3000);
  expect(await clipboard()).toBe("something the person copied since");

  // The theme: Match the system by default (light here); Dark paints at once and is kept after a reload.
  const html = panel.locator("html");
  await panel.getByRole("button", { name: "Settings" }).click();
  await expect(panel.getByRole("radio", { name: "Match the system" })).toBeChecked();
  await expect(html).not.toHaveClass(/dark/);
  await panel.getByText("Dark", { exact: true }).click();
  await expect(panel.getByRole("radio", { name: "Dark" })).toBeChecked();
  await expect(html).toHaveClass(/dark/);
  await expectAccessible(panel, "panel: settings, dark");
  await panel.reload();
  await expect(panel.getByRole("tab", { name: "Copy", selected: true })).toBeVisible();
  await expect(html).toHaveClass(/dark/);
  await expectAccessible(panel, "panel: copy, dark");
  await panel.getByRole("button", { name: "Settings" }).click();
  await panel.getByRole("radio", { name: "Light" }).focus();
  await panel.keyboard.press("ArrowLeft"); // a radio group: the arrows choose
  await expect(panel.getByRole("radio", { name: "Match the system" })).toBeChecked();
  await expect(html).not.toHaveClass(/dark/);
});
