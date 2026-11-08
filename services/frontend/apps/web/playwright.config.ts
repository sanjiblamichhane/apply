import { defineConfig, devices } from "@playwright/test";

/**
 * Browser journeys against the real backend and worker on a throwaway database (tests/e2e/global-setup.ts),
 * on their own ports (web 3399, API 8199): never your development servers or data.
 *
 *   pnpm --filter @apply/web test:e2e
 */
export default defineConfig({
  testDir: "tests/e2e",
  globalSetup: "./tests/e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,                 // one database for the run: journeys go one after another
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3399",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
