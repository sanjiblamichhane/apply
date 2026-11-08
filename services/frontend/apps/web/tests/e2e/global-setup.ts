/**
 * Everything the journeys need, started fresh and stopped after (packages/e2e-harness): Postgres, the API and
 * worker with a fake model server and recorded boards, and the web app's standalone server, on their own ports.
 */
import { cpSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { cleanEnv, startStack, waitFor } from "@apply/e2e-harness";

const WEB = fileURLToPath(new URL("../..", import.meta.url));
// APPLY_SHOTS (playwright.screenshots.config.ts): the README's screenshots, on their own stack and ports, with the demo.
const SHOTS = process.env.APPLY_SHOTS === "1";
const API_PORT = SHOTS ? 8197 : 8199;
const WEB_PORT = SHOTS ? 3397 : 3399;

export default async function globalSetup() {
  const stack = await startStack({
    name: SHOTS ? "apply-test-shots-web" : "apply-test-web",
    demo: SHOTS,
    apiPort: API_PORT,
    allowedOrigins: [`http://127.0.0.1:${WEB_PORT}`, `http://localhost:${WEB_PORT}`],
    extraEnv: { APPLY_PUBLIC_URL: `http://127.0.0.1:${WEB_PORT}` }, // the address in emailed links
  });

  // The same standalone server the container image runs, with the API's address given at start (not build).
  const clean = cleanEnv();
  if (!process.env.APPLY_E2E_SKIP_BUILD) {
    execFileSync("pnpm", ["exec", "next", "build"], { cwd: WEB, env: clean as NodeJS.ProcessEnv, stdio: "pipe" });
    cpSync(`${WEB}/.next/static`, `${WEB}/.next/standalone/apps/web/.next/static`, { recursive: true });
    if (existsSync(`${WEB}/public`)) cpSync(`${WEB}/public`, `${WEB}/.next/standalone/apps/web/public`, { recursive: true });
  }
  stack.spawn("web", process.execPath, [`${WEB}/.next/standalone/apps/web/server.js`], WEB,
    { ...clean, PORT: String(WEB_PORT), HOSTNAME: "127.0.0.1", APPLY_API_URL: stack.apiUrl });
  await waitFor(`http://127.0.0.1:${WEB_PORT}/sign-in`, "the web app");
  process.env.APPLY_E2E_MAIL_URL = stack.mailUrl; // for the journeys, which run after this

  return () => stack.stop();
}
