/**
 * The stack (packages/e2e-harness), the fake boards (packages/ats-adapters/fixtures) and the extension's test
 * build, which may reach only those boards and this API. The tests find them through APPLY_EXT_E2E.
 */
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { startFakeBoards } from "@apply/ats-adapters/fixtures";
import { cleanEnv, startStack } from "@apply/e2e-harness";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// APPLY_SHOTS (playwright.screenshots.config.ts): the README's screenshots, on their own stack and port, with the demo.
const SHOTS = process.env.APPLY_SHOTS === "1";
const API_PORT = SHOTS ? 8196 : 8198;

export default async function globalSetup() {
  const stack = await startStack({ name: SHOTS ? "apply-test-shots-extension" : "apply-test-extension", apiPort: API_PORT, demo: SHOTS });
  const boards = await startFakeBoards();
  execFileSync(process.execPath, ["scripts/build.mjs", "--test"], {
    cwd: ROOT, stdio: "pipe",
    env: { ...cleanEnv(), APPLY_EXT_TEST_BOARDS: JSON.stringify({ ...boards.hosts, [boards.other.host]: "other", [boards.board04.host]: "board04" }), APPLY_EXT_TEST_API: stack.apiUrl } as NodeJS.ProcessEnv,
  });
  process.env.APPLY_EXT_E2E = JSON.stringify({ apiUrl: stack.apiUrl, boards: { ...boards.urls, other: boards.other.url, board04: boards.board04.url }, dist: `${ROOT}/dist-test` });
  return async () => {
    await boards.close();
    await stack.stop();
  };
}
