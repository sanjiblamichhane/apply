import { describe, expect, it } from "vitest";

import { asPaste } from "@/components/paste-box";

describe("what was pasted", () => {
  it("a lone link is a link; anything else is text", () => {
    expect(asPaste("  https://jobs.example.com/1 ")).toEqual({ url: "https://jobs.example.com/1" });
    expect(asPaste("Engineer at Acme\nhttps://acme.example/apply")).toEqual({ text: "Engineer at Acme\nhttps://acme.example/apply" });
    expect(asPaste("ftp://x")).toEqual({ text: "ftp://x" });
    expect(asPaste("   ")).toBeNull();
  });
});
