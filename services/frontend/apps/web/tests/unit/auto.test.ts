import { describe, expect, it } from "vitest";

import { actionsFor, formUrl } from "@/lib/auto";

describe("Auto on the web: it prepares, the person sends", () => {
  it("offers only what can be done now, and never a send", () => {
    expect(actionsFor({ status: "ready", reason: null, application_id: "a" })).toEqual(
      { stop: true, review: true, retry: false, dismiss: false });
    expect(actionsFor({ status: "writing", reason: null, application_id: "a" }).stop).toBe(true);
    expect(actionsFor({ status: "sent", reason: null, application_id: "a" }).stop).toBe(false);
    expect(actionsFor({ status: "needs_you", reason: "AUTO_CLAIM_WARNINGS", application_id: null })).toEqual(
      { stop: false, review: false, retry: true, dismiss: true });
    // A run from before apply stopped sending, that may have gone out: never started again.
    expect(actionsFor({ status: "needs_you", reason: "AUTO_SEND_UNKNOWN", application_id: "a" }).retry).toBe(false);
    expect(actionsFor({ status: "needs_you", reason: "AUTO_NO_CONFIRMATION", application_id: "a" }).retry).toBe(false);
  });

  it("links only to a web address for the form", () => {
    const posting = "https://jobs.lever.co/acme/1";
    expect(formUrl({ opportunity: { apply_url: `${posting}/apply`, source_url: posting } })).toBe(`${posting}/apply`);
    expect(formUrl({ opportunity: { apply_url: null, source_url: posting } })).toBe(posting); // the posting, else
    expect(formUrl({ opportunity: { apply_url: "javascript:alert(1)", source_url: posting } })).toBeNull();
    expect(formUrl({ opportunity: { apply_url: null, source_url: null } })).toBeNull();
  });
});
