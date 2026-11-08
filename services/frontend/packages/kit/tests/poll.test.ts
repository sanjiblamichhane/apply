import { describe, expect, it } from "vitest";

import { backoffInterval, PollTimeoutError, pollUntilSettled } from "../src/poll";

function clock() {
  let now = 0;
  return { now: () => now, sleep: async (ms: number) => void (now += ms) };
}

describe("pollUntilSettled", () => {
  it("returns at once when the first value is already settled", async () => {
    let calls = 0;
    const value = await pollUntilSettled({ status: "ready" }, async (v) => (calls++, v), {
      isPending: (v) => v.status === "pending", intervalMs: 1000, timeoutMs: 5000, ...clock(),
    });
    expect(value.status).toBe("ready");
    expect(calls).toBe(0);
  });

  it("asks again until settled", async () => {
    const answers = ["pending", "pending", "ready"];
    const value = await pollUntilSettled("pending", async () => answers.shift()!, {
      isPending: (v) => v === "pending", intervalMs: 1000, timeoutMs: 60_000, ...clock(),
    });
    expect(value).toBe("ready");
  });

  it("gives up after the timeout rather than waiting for ever", async () => {
    await expect(pollUntilSettled("pending", async () => "pending", {
      isPending: () => true, intervalMs: 1000, timeoutMs: 3000, ...clock(),
    })).rejects.toBeInstanceOf(PollTimeoutError);
  });

  it("looks often at first, then less often", () => {
    expect(backoffInterval(0)).toBe(1000);
    expect(backoffInterval(30_000)).toBe(2000);
    expect(backoffInterval(120_000)).toBe(5000);
  });
});
