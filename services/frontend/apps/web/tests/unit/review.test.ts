import type { Answer, Document } from "@apply/api";
import { describe, expect, it } from "vitest";

import { anyPending, openWarnings } from "@/lib/documents";
import { answerText } from "@/lib/review";

const answer = (over: Partial<Answer>): Answer => ({
  id: "a", pack: "job", key: "k", question: { en: "Q", ne: "प्र" }, answer: "", answer_type: "text", choices: [],
  is_sensitive: false, source: "pack", ...over,
});

describe("answers as the kit shows them", () => {
  it("in words, in the reader's language", () => {
    expect(answerText(answer({ answer_type: "yes_no", answer: "yes" }), { yes: "हो", no: "होइन" }, "ne")).toBe("हो");
    const gender = answer({ answer_type: "choice", answer: "decline",
      choices: [{ value: "decline", label: { en: "Decline to answer", ne: "जवाफ दिन चाहन्नँ" } }] });
    expect(answerText(gender, { yes: "Yes", no: "No" }, "ne")).toBe("जवाफ दिन चाहन्नँ");
    expect(answerText(answer({ answer: "One month" }), { yes: "Yes", no: "No" }, "en")).toBe("One month");
  });
});

describe("documents under review", () => {
  const doc = (over: Partial<Document>) => ({ status: "ready", claims_status: "checked", claim_warnings: [], ...over }) as Document;
  it("are looked at again while their check runs", () => {
    expect(anyPending([doc({ claims_status: "pending" })])).toBe(true);
    expect(anyPending([doc({})])).toBe(false);
  });
  it("count the warnings not yet decided", () => {
    expect(openWarnings(doc({ claim_warnings: [
      { id: "1", kind: "number", quote: "12", reason: "r", resolved: "kept" },
      { id: "2", kind: "unsupported", quote: "fleet", reason: "r", resolved: null },
    ] }))).toBe(1);
  });
});
