import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

describe("the generated types", () => {
  it("are current with services/backend/openapi.json", () => {
    const script = fileURLToPath(new URL("../scripts/generate.mjs", import.meta.url));
    expect(() => execFileSync(process.execPath, [script, "--check"], { stdio: "pipe" })).not.toThrow();
  }, 60_000); // it generates the types afresh: seconds on a laptop, more on a shared CI runner
});
