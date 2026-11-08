import { existsSync } from "node:fs";
import { join } from "node:path";

import { boardHosts } from "@apply/ats-adapters";
import { describe, expect, it } from "vitest";

import { API_HOSTS, BOARD_HOSTS, ICON_SIZES, manifest } from "../../scripts/manifest.mjs";

describe("the manifest", () => {
  const m = manifest({ version: "0.1.0" });

  it("asks for nothing but the side panel, storage, putting its script on a site the person allows, and a page to clear the clipboard", () => {
    expect(m.permissions).toEqual(["sidePanel", "storage", "scripting", "offscreen"]);
    expect(m.manifest_version).toBe(3);
  });

  it("asks for the clipboard only when the person turns on clearing it", () => {
    expect(m.optional_permissions).toEqual(["clipboardWrite", "clipboardRead"]);
    expect(m.permissions).not.toContain("clipboardRead");
    expect(String(m.description).length).toBeLessThanOrEqual(132); // the browser's limit
  });

  it("reaches only the boards it knows and apply on this computer; any other site only when allowed", () => {
    const boards = boardHosts().map((h) => `https://${h}/*`);
    expect(m.host_permissions).toEqual([...boards, "http://127.0.0.1:8110/*", "http://localhost:8110/*"]);
    expect(m.host_permissions).toContain("https://*.myworkdayjobs.com/*");
    expect(m.content_scripts[0]!.matches).toEqual(boards);
    expect(m.optional_host_permissions).toEqual(["https://*/*", "http://*/*"]);
    expect(API_HOSTS).toEqual(["http://127.0.0.1:8110/*", "http://localhost:8110/*"]);
  });

  it("has apply's icon at every size the browser asks for, each drawn by tools/draw_mark.py", () => {
    const icons = m.icons as Record<string, string>;
    expect(Object.keys(icons)).toEqual(["16", "32", "48", "128"]);
    for (const size of ICON_SIZES) expect(existsSync(join(process.cwd(), `src/icons/icon-${size}.png`)), `icon-${size}.png`).toBe(true);
    expect((m.action as { default_icon: Record<string, string> }).default_icon["16"]).toBe("icons/icon-16.png");
  });

  it("covers exactly the boards the adapters know", () => {
    expect(BOARD_HOSTS).toEqual(boardHosts());
  });

  it("adds the journeys' fake boards only to the test build", () => {
    const test = manifest({ version: "0.1.0", testHosts: ["127.0.0.1:4011"] });
    expect(test.host_permissions).toContain("http://127.0.0.1:4011/*");
    expect(test.content_scripts[0]!.matches).toContain("http://127.0.0.1:4011/*");
    expect(JSON.stringify(m)).not.toContain("127.0.0.1:4011");
  });
});
