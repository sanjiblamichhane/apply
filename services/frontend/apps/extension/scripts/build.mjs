/**
 * Builds the unpacked extension (load it from chrome://extensions → Load unpacked).
 *
 *   node scripts/build.mjs           the release build, into dist/: boards and the local API only
 *   node scripts/build.mjs --test    the journeys' build, into dist-test/ (never dist/, so it can't be loaded by
 *                                    mistake): also the local fake boards, from APPLY_EXT_TEST_BOARDS
 *                                    ({"127.0.0.1:4011": "board01", …}) and APPLY_EXT_TEST_API (an origin)
 */
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { build } from "esbuild";

import { ICON_SIZES, manifest } from "./manifest.mjs";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const test = process.argv.includes("--test");
const DIST = join(ROOT, test ? "dist-test" : "dist");
const aliases = test ? JSON.parse(process.env.APPLY_EXT_TEST_BOARDS || "{}") : {};
const testApi = test ? process.env.APPLY_EXT_TEST_API || "" : "";
const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });

const define = {
  __BOARD_ALIASES__: JSON.stringify(aliases),
  __DEFAULT_API__: JSON.stringify(testApi || "http://127.0.0.1:8110"),
  __CLEAR_AFTER_MS__: test ? "1500" : "60000",
  "process.env.NODE_ENV": '"production"',
};
const common = { bundle: true, minify: !test, sourcemap: test ? "inline" : false, target: "chrome116", define, logLevel: "warning" };
await build({ ...common, entryPoints: [join(ROOT, "src/background.ts")], outfile: join(DIST, "background.js"), format: "esm" });
await build({ ...common, entryPoints: [join(ROOT, "src/content.ts")], outfile: join(DIST, "content.js"), format: "iife" });
await build({ ...common, entryPoints: [join(ROOT, "src/offscreen.ts")], outfile: join(DIST, "offscreen.js"), format: "esm" });
await build({ ...common, entryPoints: [join(ROOT, "src/panel/main.tsx")], outfile: join(DIST, "panel.js"), format: "esm", jsx: "automatic" });

// The panel's styles: the web app's theme through Tailwind, with the fonts it names copied beside it.
execFileSync(join(ROOT, "node_modules/.bin/tailwindcss"), ["-i", join(ROOT, "src/panel/panel.css"), "-o", join(DIST, "panel.css"), "--minify"], { cwd: ROOT, stdio: "pipe" });
const css = readFileSync(join(DIST, "panel.css"), "utf8");
const require = createRequire(join(ROOT, "../../packages/ui/package.json"));
const fontDirs = ["@fontsource-variable/inter", "@fontsource-variable/noto-sans-devanagari"]
  .map((p) => join(dirname(require.resolve(`${p}/package.json`)), "files"));
mkdirSync(join(DIST, "files"));
for (const name of new Set([...css.matchAll(/url\(\.\/files\/([^)]+)\)/g)].map((m) => m[1]))) {
  const from = fontDirs.map((d) => join(d, name)).find((f) => { try { readFileSync(f); return true; } catch { return false; } });
  if (from) copyFileSync(from, join(DIST, "files", name));
}

copyFileSync(join(ROOT, "src/panel/panel.html"), join(DIST, "panel.html"));
copyFileSync(join(ROOT, "src/offscreen.html"), join(DIST, "offscreen.html"));
// The icons tools/draw_mark.py draws: the toolbar, chrome://extensions and the store.
mkdirSync(join(DIST, "icons"));
for (const size of ICON_SIZES) copyFileSync(join(ROOT, `src/icons/icon-${size}.png`), join(DIST, `icons/icon-${size}.png`));
const testHosts = [...Object.keys(aliases), ...(testApi ? [new URL(testApi).host] : [])];
writeFileSync(join(DIST, "manifest.json"), JSON.stringify(manifest({ version: pkg.version, testHosts, test }), null, 2));
console.log(`extension built into ${DIST}${test ? " (test build)" : ""}`);
