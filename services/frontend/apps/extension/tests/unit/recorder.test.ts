import { describe, expect, it } from "vitest";

import type { ExtensionApi } from "../../src/api";
import type { Store } from "../../src/config";
import { pendingKey, recordedKey, type PendingFill } from "../../src/messages";
import { makeRecorder } from "../../src/recorder";

function memory(): Store & { data: Record<string, unknown> } {
  const data: Record<string, unknown> = {};
  return {
    data,
    get: async (key) => (key in data ? { [key]: data[key] } : {}),
    set: async (items) => { Object.assign(data, items); },
    remove: async (key) => { delete data[key]; },
  };
}

function api(fail = false) {
  const calls: string[] = [];
  const client = {
    submit: async (id: string) => {
      calls.push(`submit ${id}`);
      if (fail) throw Object.assign(new Error("x"), { code: "NETWORK" });
      return { id: "sub1" };
    },
    application: async () => ({ stage: { code: "in_progress" } }),
  } as unknown as ExtensionApi;
  return { calls, client };
}

const pending: PendingFill = { applicationId: "app1", filled: { fields: 4, files: ["resume"], left_blank: [] }, at: 1000 };

describe("recording a submission", () => {
  it("records once per filled form, however often the thank-you page is seen", async () => {
    const session = memory();
    session.data[pendingKey(7)] = pending;
    const { calls, client } = api();
    const record = makeRecorder(session, async () => client, () => 2000);
    const [first, second] = await Promise.all([record(7, "https://x/thanks"), record(7, "https://x/thanks")]);
    expect(first).toMatchObject({ applicationId: "app1", submissionId: "sub1", stageCode: "in_progress" });
    expect(second).toBeNull();
    expect(await record(7, "https://x/thanks")).toBeNull(); // reloaded later: nothing pending any more
    expect(calls).toEqual(["submit app1"]);
    expect(session.data[recordedKey(7)]).toMatchObject({ submissionId: "sub1" });
  });

  it("does nothing on a tab the extension didn't fill, or filled long ago", async () => {
    const session = memory();
    const { calls, client } = api();
    expect(await makeRecorder(session, async () => client, () => 2000)(8, "https://x/thanks")).toBeNull();
    session.data[pendingKey(8)] = pending;
    expect(await makeRecorder(session, async () => client, () => 1000 + 7 * 3600_000)(8, "https://x/thanks")).toBeNull();
    expect(calls).toEqual([]);
  });

  it("keeps the fill when recording fails, so it can be tried again", async () => {
    const session = memory();
    session.data[pendingKey(9)] = pending;
    const { client } = api(true);
    const recorded = await makeRecorder(session, async () => client, () => 2000)(9, "https://x/thanks");
    expect(recorded).toMatchObject({ error: "NETWORK" });
    expect(session.data[pendingKey(9)]).toEqual(pending);
  });
});
