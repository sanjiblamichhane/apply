import { defineConfig } from "@playwright/test";

/**
 * The extension's journeys: the unpacked test build in a real browser, against the real API and worker on a
 * throwaway database (port 8198) and fake boards on their own local ports (tests/e2e/global-setup.ts).
 *
 *   pnpm --filter @apply/extension test:e2e
 */
export default defineConfig({
  testDir: "tests/e2e",
  globalSetup: "./tests/e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: { trace: "retain-on-failure", screenshot: "only-on-failure" },
});
