import { defineConfig } from "@playwright/test";

/**
 * The README's screenshots of the extension (demo/images/extension-*.png): the test build beside the fake boards,
 * on a throwaway stack with the demo (John Doe, fictional) and the fake model server. Run when the panel changes,
 * not with the tests:
 *
 *   pnpm --filter @apply/extension screenshots
 */
process.env.APPLY_SHOTS = "1";

export default defineConfig({
  testDir: "tests/screenshots",
  globalSetup: "./tests/e2e/global-setup.ts",
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
});
