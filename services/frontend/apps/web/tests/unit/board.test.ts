import type { Application, Stage } from "@apply/api";
import { describe, expect, it } from "vitest";

import { boardStages, documentBadges, filterApplications, readListState, writeListState } from "@/lib/board";

const app = (id: string, title: string, issuer: string, docs: Application["current_documents"] = []): Application => ({
  id, profile_id: null, pipeline_id: "p", submitted_at: null, notes: "", created_at: "", updated_at: "",
  stage: { id: "s1", code: "new", category: "active" }, current_documents: docs,
  opportunity: { id: `o${id}`, pack: "job", title, issuer_name: issuer, deadline: null, apply_url: null, source_url: null,
                 extraction: { status: "ready", method: "model" } },
});

describe("the list's URL state", () => {
  it("reads board by default, and the filter", () => {
    expect(readListState(new URLSearchParams(""))).toEqual({ view: "board", query: "" });
    expect(readListState(new URLSearchParams("view=list&q=%20data%20"))).toEqual({ view: "list", query: "data" });
    expect(readListState(new URLSearchParams("view=nonsense")).view).toBe("board");
  });

  it("writes only what isn't the default", () => {
    expect(writeListState(new URLSearchParams("view=list"), { view: "board" })).toBe("");
    expect(writeListState(new URLSearchParams(""), { view: "list", query: "acme" })).toBe("?view=list&q=acme");
    expect(writeListState(new URLSearchParams("q=x"), { query: "  " })).toBe("");
  });
});

describe("filtering", () => {
  const items = [app("1", "Senior Backend Engineer", "Acme Robotics"), app("2", "Data Analyst", "Example Retail"),
                 app("3", "Développeur", "Société Exemple")];
  it("matches every word, in the title or the company, any case", () => {
    expect(filterApplications(items, "backend acme").map((a) => a.id)).toEqual(["1"]);
    expect(filterApplications(items, "RETAIL").map((a) => a.id)).toEqual(["2"]);
    expect(filterApplications(items, "").length).toBe(3);
  });
  it("ignores accents", () => {
    expect(filterApplications(items, "developpeur societe").map((a) => a.id)).toEqual(["3"]);
  });
});

describe("board stages", () => {
  it("are in order, without archived ones", () => {
    const stages = [
      { id: "b", code: "b", position: 2, is_archived: false }, { id: "a", code: "a", position: 1, is_archived: false },
      { id: "x", code: "x", position: 0, is_archived: true },
    ] as Stage[];
    expect(boardStages(stages).map((s) => s.code)).toEqual(["a", "b"]);
  });
});

describe("document badges", () => {
  it("come from the newest document of each type", () => {
    const a = app("1", "t", "c", [
      { id: "01B", document_type: "resume", status: "pending", version: 0 },
      { id: "01A", document_type: "resume", status: "ready", version: 1 },
      { id: "01C", document_type: "cover_letter", status: "failed", version: 0 },
    ]);
    expect(documentBadges(a, ["resume", "cover_letter", "other"])).toEqual({ resume: "pending", cover_letter: "failed", other: "none" });
  });
});
