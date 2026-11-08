/**
 * What browser journeys run against, started fresh and stopped after: Postgres, a storage emulator and a local mail catcher
 * (compose.test.yml as a named project per suite: no anonymous container or volume), the real migrations, the
 * owner account, a fake model server, the recorded job-board APIs, the API and the worker. Each suite runs on its own
 * ports; nothing touches your development database or bucket, your servers, or a real board.
 */
import { type ChildProcess, execFileSync, spawn } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";

export const BACKEND = fileURLToPath(new URL("../../../../backend", import.meta.url));
const COMPOSE_FILE = fileURLToPath(new URL("../../../../../compose.test.yml", import.meta.url));

/** compose.test.yml as the project ``name``: its containers and network are named after it. */
function compose(name: string, ...args: string[]): string {
  return execFileSync("docker", ["compose", "-f", COMPOSE_FILE, "-p", name, ...args], {
    env: { ...process.env, APPLY_TEST_STACK: name } as NodeJS.ProcessEnv,
    stdio: ["ignore", "pipe", "pipe"],
  }).toString().trim();
}

const hostPort = (name: string, service: string, port: number) => compose(name, "port", service, String(port)).split(":").pop();
export const OWNER = { email: "owner@example.com", password: "correct horse battery staple" };

export type Env = Record<string, string | undefined>;

export async function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => (typeof address === "object" && address ? resolve(address.port) : reject(new Error("no port"))));
    });
  });
}

export async function waitFor(url: string, what: string, seconds = 90): Promise<void> {
  const deadline = Date.now() + seconds * 1000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { redirect: "manual" });
      if (response.status < 500) return;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`${what} did not start at ${url}`);
}

export function start(name: string, command: string, args: string[], cwd: string, env: Env): ChildProcess {
  const child = spawn(command, args, { cwd, env: env as NodeJS.ProcessEnv, stdio: ["ignore", "pipe", "pipe"] });
  const log = (chunk: Buffer) => {
    if (process.env.APPLY_E2E_LOGS) process.stdout.write(`[${name}] ${chunk}`);
  };
  child.stdout?.on("data", log);
  child.stderr?.on("data", log);
  return child;
}

/** process.env without any APPLY_* setting: the journeys never run on yours. */
export function cleanEnv(): Env {
  return Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("APPLY_")));
}

export interface Stack {
  apiUrl: string;
  /** This suite's mail catcher (its API at /api/v1): the emails apply sent. */
  mailUrl: string;
  env: Env;
  /** Run `apply …` against this stack's database. */
  apply(args: string[], input?: string): Buffer;
  /** Start another process alongside (stopped with the stack). */
  spawn(name: string, command: string, args: string[], cwd: string, env: Env): ChildProcess;
  stop(): Promise<void>;
}

export interface StackOptions {
  /** The compose project for this suite's database and bucket: apply-test-web, apply-test-extension, … */
  name: string;
  apiPort: number;
  /** Origins a browser may send unsafe requests from (the web app's). */
  allowedOrigins?: string[];
  /** More APPLY_* settings for this suite (the web app's address in emailed links, say). */
  extraEnv?: Env;
  /** Put the demo (John Doe, fictional) in the owner's account: for the README's screenshots. */
  demo?: boolean;
}

export async function startStack({ name, apiPort, allowedOrigins = [], extraEnv = {}, demo = false }: StackOptions): Promise<Stack> {
  compose(name, "down", "-v", "--remove-orphans"); // whatever an interrupted run left
  compose(name, "up", "-d", "--wait", "postgres", "storage", "mail");
  const databaseUrl = `postgresql+asyncpg://apply:apply-test@127.0.0.1:${hostPort(name, "postgres", 5432)}/apply`;
  const storageUrl = `http://127.0.0.1:${hostPort(name, "storage", 4443)}`;
  await waitFor(`${storageUrl}/storage/v1/b`, "the bucket emulator");
  const mailUrl = `http://127.0.0.1:${hostPort(name, "mail", 8025)}`;
  await waitFor(`${mailUrl}/readyz`, "the mail catcher");
  const modelPort = await freePort();
  const boardsPort = await freePort();

  const env: Env = {
    ...cleanEnv(),
    APPLY_ENV: "test",
    APPLY_DATABASE_URL: databaseUrl,
    APPLY_STORAGE_ENDPOINT: storageUrl,
    APPLY_STORAGE_BUCKET: "apply-e2e",
    APPLY_PORT: String(apiPort),
    APPLY_ALLOWED_ORIGINS: JSON.stringify(allowedOrigins),
    APPLY_LLM_BASE_URL: `http://127.0.0.1:${modelPort}`,
    // Settings → Model looks only at the fake: never at a model server running on this machine.
    APPLY_LLM_DISCOVER_PORTS: "[]",
    APPLY_LLM_MODEL: "writer:8b",
    APPLY_LLM_TIMEOUT: "30",
    APPLY_WORKER_POLL_SECONDS: "0.2",
    APPLY_LANG: "en",
    // The job boards' APIs are recorded answers on this machine; nothing reaches the real boards.
    APPLY_SOURCE_BASE_URLS: JSON.stringify(Object.fromEntries(
      ["board01", "board02", "board03"].map((kind) => [kind, `http://127.0.0.1:${boardsPort}`]))),
    APPLY_FETCH_ALLOW_PRIVATE: "1",
    APPLY_SCHEDULER_TICK_SECONDS: "1",
    // Email goes to this suite's mail catcher, read back with mailUrl; never anywhere real.
    APPLY_SMTP_HOST: "127.0.0.1",
    APPLY_SMTP_PORT: hostPort(name, "mail", 1025),
    APPLY_SMTP_SECURITY: "none",
    ...extraEnv,
  };
  const apply = (args: string[], input?: string) =>
    execFileSync("uv", ["run", "apply", ...args], { cwd: BACKEND, env: env as NodeJS.ProcessEnv, input, stdio: ["pipe", "pipe", "pipe"] });

  apply(["migrate"]);
  apply(["init", "--email", OWNER.email, "--password-stdin"], `${OWNER.password}\n`);

  const children: ChildProcess[] = [
    start("model", "uv", ["run", "python", "-m", "tests.support.e2e_model_server", "--port", String(modelPort)], BACKEND, env),
    start("boards", "uv", ["run", "python", "-m", "tests.support.e2e_boards", "--port", String(boardsPort)], BACKEND, env),
    start("api", "uv", ["run", "apply", "serve", "--no-migrate", "--log-level", "warning"], BACKEND, env),
    start("worker", "uv", ["run", "apply", "worker"], BACKEND, env),
  ];
  const apiUrl = `http://127.0.0.1:${apiPort}`;
  await waitFor(`${apiUrl}/api/v1/health`, "the API");
  // After the API is up: it registers the packs the demo's profile belongs to.
  if (demo) apply(["demo", "--email", OWNER.email, "--force"]);

  return {
    apiUrl,
    mailUrl,
    env,
    apply,
    spawn(name, command, args, cwd, childEnv) {
      const child = start(name, command, args, cwd, childEnv);
      children.push(child);
      return child;
    },
    async stop() {
      for (const child of children) child.kill("SIGTERM");
      compose(name, "down", "-v", "--remove-orphans");
    },
  };
}

/** Sign in as the owner over HTTP: the session cookie, for setting things up through the API. */
export async function ownerSession(apiUrl: string): Promise<string> {
  const response = await fetch(`${apiUrl}/api/v1/auth/sign-in`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(OWNER),
  });
  if (!response.ok) throw new Error(`sign-in failed: ${response.status} ${await response.text()}`);
  const cookie = response.headers.getSetCookie().find((c) => c.includes("apply_session"));
  if (!cookie) throw new Error("no session cookie");
  return cookie.split(";")[0]!;
}
