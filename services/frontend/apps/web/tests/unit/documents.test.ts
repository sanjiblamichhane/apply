import type { Document } from "@apply/api";
import { describe, expect, it } from "vitest";

import { confirmMarkers, documentState, downloadName, versions } from "@/lib/documents";

const doc = (id: string, status: Document["status"], version: number, is_active: boolean, type = "resume"): Document => ({
  id, application_id: "a", document_type: type, status, error_code: status === "failed" ? "LLM_UNREACHABLE" : null,
  version, is_active, content_markdown: `v${version}`, claim_warnings: [], source: "generated", model: "m",
  generation_ms: 100, profile_id: null, created_at: "", finished_at: null, claims_status: "checked",
  claims_checked_at: null, reviewed_at: null,
});

describe("documentState", () => {
  it("none, before anything is asked for", () => {
    expect(documentState([], "resume")).toEqual({ kind: "none" });
  });

  it("the version in use stays shown while a new one is written", () => {
    const state = documentState([doc("01B", "pending", 0, false), doc("01A", "ready", 1, true)], "resume");
    expect(state.kind).toBe("pending");
    expect(state.kind === "pending" && state.current?.version).toBe(1);
  });

  it("a failure is shown, above the version still in use", () => {
    const state = documentState([doc("01C", "failed", 0, false), doc("01A", "ready", 1, true)], "resume");
    expect(state.kind === "failed" && state.failed.error_code).toBe("LLM_UNREACHABLE");
    expect(state.kind === "failed" && state.current?.version).toBe(1);
  });

  it("a newer success clears an older failure", () => {
    const state = documentState([doc("01D", "ready", 2, true), doc("01C", "failed", 0, false), doc("01A", "ready", 1, false)], "resume");
    expect(state).toEqual({ kind: "ready", current: expect.objectContaining({ version: 2 }) });
  });

  it("other types don't count", () => {
    expect(documentState([doc("01A", "ready", 1, true, "cover_letter")], "resume")).toEqual({ kind: "none" });
  });
});

describe("helpers", () => {
  it("lists finished versions, newest first", () => {
    expect(versions([doc("1", "ready", 1, false), doc("3", "pending", 0, false), doc("2", "ready", 2, true)], "resume")
      .map((d) => d.version)).toEqual([2, 1]);
  });
  it("counts the markers left to check", () => {
    expect(confirmMarkers("Led [CONFIRM: team size] engineers; cut [CONFIRM: %] costs")).toBe(2);
    expect(confirmMarkers("Nothing to check")).toBe(0);
  });
  it("names a download safely", () => {
    expect(downloadName("Senior Backend Engineer / Acme!", "resume", 2)).toBe("senior-backend-engineer-acme-resume-v2.md");
    expect(downloadName("", "cover_letter", 1)).toBe("cover-letter-v1.md");
  });
});
