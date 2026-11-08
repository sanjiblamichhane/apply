import { defineConfig } from "@playwright/test";

/**
 * The README's screenshots of the web app (demo/images/web-*.png), taken on a throwaway stack with the demo
 * (John Doe, fictional) and the fake model server: never your development servers or data. Run when the screens
 * change, not with the tests:
 *
 *   pnpm --filter @apply/web screenshots
 */
process.env.APPLY_SHOTS = "1";

export default defineConfig({
  testDir: "tests/screenshots",
  globalSetup: "./tests/e2e/global-setup.ts",
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:3397", viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 },
});
