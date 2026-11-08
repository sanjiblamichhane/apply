/**
 * The README's pictures of the extension, in a realistic case: John Doe (the demo) opens a job's application form
 * on a supported board, sees what apply would fill, confirms, and checks the filled form before pressing Submit
 * himself. Also the Copy view. Written to demo/images at the repo's root.
 */
import { fileURLToPath } from "node:url";

import type { Page } from "@playwright/test";

import { connect, expect, openPanel, setup, test } from "../e2e/fixtures";
import { dressAsPortal } from "./portal";

const IMAGES = fileURLToPath(new URL("../../../../../../demo/images/", import.meta.url));
const PANEL = { width: 420, height: 900 };
const FORM = { width: 1000, height: 900 };

async function settle(page: Page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
}

/** Two pictures side by side, as the browser shows the page and its side panel. */
async function sideBySide(page: Page, left: Buffer, right: Buffer, name: string) {
  const src = (b: Buffer) => `data:image/png;base64,${b.toString("base64")}`;
  await page.setViewportSize({ width: FORM.width + PANEL.width + 1, height: FORM.height });
  await page.setContent(`<body style="margin:0;display:flex;background:#d4d4d4;gap:1px">
    <img src="${src(left)}" style="width:${FORM.width}px"><img src="${src(right)}" style="width:${PANEL.width}px"></body>`);
  await page.waitForLoadState("load");
  await page.screenshot({ path: `${IMAGES}${name}.png` });
}

test("the extension fills a real-looking application form for John Doe", async ({ context, extensionId, apply, token }) => {
  const board = await context.newPage();
  await board.setViewportSize(FORM);
  await board.goto(setup.boards.board01);
  // The bare fake form, dressed as a company's careers page (only the look changes; the fields stay as they are).
  await dressAsPortal(board);
  const panel = await openPanel(context, extensionId, board);
  await panel.setViewportSize(PANEL);
  await connect(panel, token, "copy");

  // Copy: John Doe's profile beside any page, a click away from the clipboard.
  await expect(panel.getByRole("button", { name: "Profile: John Doe" }).or(panel.getByText("John Doe").first())).toBeVisible();
  await settle(panel);
  await panel.screenshot({ path: `${IMAGES}extension-copy.png` });

  // Fill: track the job, its documents written (by the fake model), then the preview beside the empty form.
  await panel.getByRole("tab", { name: "Fill" }).click();
  await panel.getByRole("button", { name: "Track this job" }).click();
  await expect(panel.getByText(/No documents yet/)).toBeVisible();
  const found = await apply.call<{ application: { id: string } }>("GET",
    `/api/v1/applications/by-url?url=${encodeURIComponent(setup.boards.board01)}`);
  await apply.writeDocuments(found.application.id);
  await panel.reload();
  await expect(panel.getByRole("heading", { name: /^apply will fill/ })).toBeVisible();
  await expect(panel.getByText("john.doe@example.com").first()).toBeVisible();
  await settle(panel);
  await settle(board);
  await sideBySide(await context.newPage(), await board.screenshot(), await panel.screenshot(), "extension-fill-preview");

  // Confirmed: the form filled, files attached, and what's left for John, who presses Submit himself.
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByText(/^Filled \d+ fields$/)).toBeVisible();
  await expect(board.locator("#first_name")).toHaveValue("John");
  // Filling leaves the page at the last field it touched; show it from the top, where the filled details start.
  await board.evaluate(() => window.scrollTo(0, 0));
  await settle(panel);
  await settle(board);
  await sideBySide(await context.newPage(), await board.screenshot(), await panel.screenshot(), "extension-filled");
});
