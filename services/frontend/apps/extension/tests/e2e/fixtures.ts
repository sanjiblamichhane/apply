/**
 * The extension loaded in the test browser, its id, the owner's session for setting things up through the API, and a
 * way to open the side panel (as a tab: Playwright can't open the browser's side panel) aimed at a board's tab.
 */
import AxeBuilder from "@axe-core/playwright";
import { OWNER, ownerSession } from "@apply/e2e-harness";
import { test as base, chromium, expect, type BrowserContext, type Page } from "@playwright/test";

interface Setup { apiUrl: string; boards: Record<"board01" | "board02" | "board03" | "other" | "board04", string>; dist: string }
export const setup: Setup = JSON.parse(process.env.APPLY_EXT_E2E ?? "{}");

export const PROFILE = {
  pack: "job", kind: "individual", name: "Backend", summary: "Backend engineer who ships reliable APIs.", is_default: true,
  attributes: {
    full_name: "Sam Rai", email: "sam@example.com", phone: "+977 980 000 0000", location: "Kathmandu, Nepal",
    links: [{ label: "Profile", url: "https://www.linkedin.com/in/example" }, { label: "", url: "https://github.com/example" }],
    skills: ["Python", "Django", "PostgreSQL"],
    experience: [{ title: "Backend Engineer", organisation: "Himal Tech", start: "2019", end: "", highlights: ["Built Django REST APIs"] }],
  },
};

export class Apply {
  constructor(readonly cookie: string) {}

  async call<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${setup.apiUrl}${path}`, {
      method, headers: { cookie: this.cookie, "content-type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await response.text();
    if (!response.ok && response.status !== 409) throw new Error(`${method} ${path}: ${response.status} ${text}`);
    return (text ? JSON.parse(text) : null) as T;
  }

  /** Wait for the application's resume and cover letter to be written and checked. */
  async writeDocuments(applicationId: string): Promise<void> {
    for (const type of ["resume", "cover_letter"]) {
      await this.call("POST", `/api/v1/applications/${applicationId}/documents`, { document_type: type });
    }
    for (let i = 0; i < 200; i++) {
      const docs = await this.call<{ items: { status: string; claims_status: string; is_active: boolean }[] }>(
        "GET", `/api/v1/applications/${applicationId}/documents`);
      if (docs.items.filter((d) => d.is_active && d.status === "ready" && d.claims_status !== "pending").length === 2) return;
      await new Promise((r) => setTimeout(r, 150));
    }
    throw new Error("the documents were never written");
  }
}

type Fixtures = { context: BrowserContext; extensionId: string; apply: Apply; token: string };

export const test = base.extend<Fixtures>({
  // eslint-disable-next-line no-empty-pattern
  context: async ({}, provide) => {
    const context = await chromium.launchPersistentContext("", {
      channel: "chromium",
      headless: !process.env.APPLY_E2E_HEADED,
      args: [`--disable-extensions-except=${setup.dist}`, `--load-extension=${setup.dist}`],
    });
    await provide(context);
    await context.close();
  },
  extensionId: async ({ context }, provide) => {
    let [worker] = context.serviceWorkers();
    if (!worker) worker = await context.waitForEvent("serviceworker");
    await provide(new URL(worker.url()).host);
  },
  apply: async ({}, provide) => { // eslint-disable-line no-empty-pattern
    await provide(new Apply(await ownerSession(setup.apiUrl)));
  },
  token: async ({ apply }, provide) => {
    const made = await apply.call<{ secret: string }>("POST", "/api/v1/tokens", {
      name: "The test browser", scopes: ["applications:read", "applications:write", "submissions:write", "profiles:read"],
    });
    await provide(made.secret);
  },
});
export { expect, OWNER };

/** The panel page, pointed at the tab showing ``boardPage``. */
export async function openPanel(context: BrowserContext, extensionId: string, boardPage?: Page): Promise<Page> {
  const panel = await context.newPage();
  await panel.goto(`chrome-extension://${extensionId}/panel.html`);
  if (boardPage) {
    const url = boardPage.url();
    const tabId = await panel.evaluate(async (u) => (await chrome.tabs.query({})).find((t) => t.url === u)?.id, url);
    if (!tabId) throw new Error(`no tab for ${url}`);
    await panel.goto(`chrome-extension://${extensionId}/panel.html?tab=${tabId}`);
  }
  return panel;
}

/** Connect the extension through its own form, as a person would; then show Fill (or stay on Copy). */
export async function connect(panel: Page, token: string, view: "fill" | "copy" = "fill"): Promise<void> {
  await expect(panel.getByRole("heading", { name: /Connect to apply|apply सँग जोड्नुहोस्/ })).toBeVisible();
  await expect(panel.locator("#address")).toHaveValue(setup.apiUrl);
  await panel.locator("#token").fill(token);
  await panel.getByRole("button", { name: /^Connect$|^जोड्नुहोस्$/ }).click();
  // Connected: Copy is what the panel shows first (the account is under Settings).
  await expect(panel.getByRole("tab", { name: /^Copy$|^कपी$/, selected: true })).toBeVisible();
  if (view === "fill") await panel.getByRole("tab", { name: /^Fill$|^भर्ने$/ }).click();
}

export async function expectAccessible(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.help}\n  ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join("\n  ")}`);
  expect(summary, `${label}: accessibility violations`).toEqual([]);
}

export async function received(board: keyof Setup["boards"]) {
  const response = await fetch(new URL("/__received", setup.boards[board]));
  return (await response.json()) as { fields: Record<string, string>; files: { field: string; filename: string; head: string }[] }[];
}
