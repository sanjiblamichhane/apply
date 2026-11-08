import type { FillSheet, Lookup } from "@apply/api";
import { describe, expect, it } from "vitest";

import type { PageInfo, Recorded } from "../../src/messages";
import { decide, filledSummary, toBase64 } from "../../src/panel/state";

const page: PageInfo = {
  url: "https://jobs.lever.co/himal/x/apply", board: "board02", isForm: true, ready: true, isConfirmation: false,
  signIn: false, steps: false, formKey: "3-abc", postingUrls: ["https://jobs.lever.co/himal/x"], title: "Himal",
};
const lookup = { opportunity: { id: "o" }, application: { id: "a" } } as unknown as Lookup;
const sheet = { application: { id: "a" } } as unknown as FillSheet;
const now = 1_000_000_000;

describe("what the panel shows", () => {
  it("asks to connect first", () => expect(decide({ connected: false }).kind).toBe("connect"));

  it("tells an unsupported page from a board page loaded before the extension", () => {
    expect(decide({ connected: true, page: null, onBoardHost: false }).kind).toBe("unsupported");
    expect(decide({ connected: true, page: null, onBoardHost: true }).kind).toBe("reload");
    expect(decide({ connected: true, page: { ...page, board: "other", isForm: false } }).kind).toBe("unsupported");
  });

  it("on a board's job page, says to press Apply; on its sign-in step, to sign in (never done for them)", () => {
    expect(decide({ connected: true, page: { ...page, isForm: false } })).toEqual({ kind: "job_page" });
    const signIn = { ...page, board: "board04" as const, isForm: false, signIn: true };
    expect(decide({ connected: true, page: signIn })).toEqual({ kind: "sign_in" });
  });

  it("keeps a fill's result with its step: the next step of a form starts with none", () => {
    const result = { filled: 4, attached: [], leftBlank: [] };
    expect(decide({ connected: true, page, lookup, sheet, result, resultFor: "3-abc" })).toMatchObject({ result });
    expect(decide({ connected: true, page: { ...page, formKey: "2-def" }, lookup, sheet, result, resultFor: "3-abc" }))
      .toMatchObject({ kind: "ready", result: null });
  });

  it("waits for a form drawn by script", () => {
    expect(decide({ connected: true, page: { ...page, ready: false } }).kind).toBe("waiting");
  });

  it("offers to track a posting apply doesn't have, or has without an application", () => {
    expect(decide({ connected: true, page, lookup: null })).toMatchObject({ kind: "untracked", opportunity: null });
    const known = { ...lookup, application: null } as Lookup;
    expect(decide({ connected: true, page, lookup: known })).toMatchObject({ kind: "untracked", opportunity: { id: "o" } });
  });

  it("is ready to fill once the sheet is here", () => {
    expect(decide({ connected: true, page, lookup }).kind).toBe("loading");
    expect(decide({ connected: true, page, lookup, sheet })).toMatchObject({ kind: "ready", result: null });
  });

  it("shows a fresh recording on the thank-you page, and not an old one on a new form", () => {
    const recorded: Recorded = { applicationId: "a", submissionId: "s", stageCode: "in_progress", at: now - 1000 };
    const thanks = { ...page, isForm: false, isConfirmation: true };
    expect(decide({ connected: true, page: thanks, recorded }, now).kind).toBe("recorded");
    expect(decide({ connected: true, page: thanks, recorded: { ...recorded, at: now - 2 * 3600_000 } }, now).kind).toBe("unsupported");
    expect(decide({ connected: true, page, lookup, sheet, recorded }, now).kind).toBe("ready");
  });
});

it("keeps counts and labels of a fill, never values", () => {
  expect(filledSummary({ filled: 3, attached: ["resume"], leftBlank: [{ label: "Why us?", reason: "unknown", required: true }] }))
    .toEqual({ fields: 3, files: ["resume"], left_blank: ["Why us?"] });
});

it("encodes a PDF for the content script", () => {
  const bytes = new Uint8Array(100_000).map((_, i) => i % 256);
  expect(atob(toBase64(bytes.buffer)).length).toBe(100_000);
});
