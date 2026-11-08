/**
 * The extension's manifest. Host permissions are only the boards in packages/ats-adapters/src/boards.json and
 * apply's API on this computer (plan §9.2). Another API address, or another site to fill forms on, is asked
 * for at run time, for that one origin, when the person chooses it (scripting then puts the content script
 * there). The test build adds the journeys' local fake boards and test API, and nothing else.
 */
import BOARDS from "../../../packages/ats-adapters/src/boards.json" with { type: "json" };

export const BOARD_HOSTS = Object.values(BOARDS.boards).flatMap((b) => b.hosts);
/** The icon sizes the browser asks for (src/icons, drawn by tools/draw_mark.py). */
export const ICON_SIZES = [16, 32, 48, 128];

export const API_HOSTS = ["http://127.0.0.1:8110/*", "http://localhost:8110/*"];

/**
 * @param {{ version: string, testHosts?: string[], test?: boolean }} options  testHosts: "127.0.0.1:4011" and the
 *   like; test: the journeys' build, which has the clipboard permissions from the start (a test can't answer
 *   the browser's prompt for them)
 */
export function manifest({ version, testHosts = [], test: testBuild = false }) {
  const boards = BOARD_HOSTS.map((h) => `https://${h}/*`);
  const test = testHosts.map((h) => `http://${h}/*`);
  return {
    manifest_version: 3,
    name: "apply",
    version,
    description: "Your apply profile beside every form: click a value to copy it. Fills known boards; you check and press Submit.",
    homepage_url: "https://github.com/sanjiblamichhane/apply",
    minimum_chrome_version: "116",
    icons: Object.fromEntries(ICON_SIZES.map((s) => [String(s), `icons/icon-${s}.png`])),
    action: { default_title: "apply", default_icon: Object.fromEntries(ICON_SIZES.slice(0, 2).map((s) => [String(s), `icons/icon-${s}.png`])) },
    side_panel: { default_path: "panel.html" },
    background: { service_worker: "background.js", type: "module" },
    permissions: ["sidePanel", "storage", "scripting", "offscreen", ...(testBuild ? ["clipboardWrite", "clipboardRead"] : [])],
    // Asked for only when the person turns on "Clear the clipboard a minute after copying".
    optional_permissions: ["clipboardWrite", "clipboardRead"],
    host_permissions: [...boards, ...API_HOSTS, ...test],
    optional_host_permissions: ["https://*/*", "http://*/*"],
    content_scripts: [{ matches: [...boards, ...test], js: ["content.js"], run_at: "document_idle" }],
    content_security_policy: { extension_pages: "script-src 'self'; object-src 'self'" },
  };
}
