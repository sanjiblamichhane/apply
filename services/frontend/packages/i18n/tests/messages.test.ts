import { describe, expect, it } from "vitest";

import { errors, fill, forPack, formatDate, formatRelative, messages, pick, translator } from "../src";

const DEVANAGARI = /[ऀ-ॿ]/;
// Kept the same in both languages on purpose: the product's name, a language's own name, and codes.
const SAME_IN_BOTH = new Set(["app.name", "language.en", "language.ne", "review.pdf", "profiles.form.item"]);
const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

const all = { ...messages, ...Object.fromEntries(Object.entries(errors).map(([k, v]) => [`error.${k}`, v])) };

describe("every message", () => {
  for (const [key, entry] of Object.entries(all)) {
    it(`${key} is in English and Nepali`, () => {
      expect(entry.en.trim(), `${key} has no English`).not.toBe("");
      expect(entry.ne.trim(), `${key} has no Nepali`).not.toBe("");
      if (!SAME_IN_BOTH.has(key)) expect(entry.ne, `${key}: the Nepali isn't in Devanagari`).toMatch(DEVANAGARI);
      expect(placeholders(entry.ne), `${key}: placeholders differ`).toEqual(placeholders(entry.en));
    });
  }
});

describe("t()", () => {
  it("fills placeholders, with the reader's digits", () => {
    expect(translator("en")("applications.count", { count: 12 })).toBe("12 applications");
    expect(translator("ne")("applications.count", { count: 12 })).toBe("१२ आवेदन");
    expect(translator("ne")("time.seconds", { count: 1.5 })).toBe("१.५ सेकेन्ड");
  });

  it("leaves an unknown placeholder visible rather than silently empty", () => {
    expect(fill("Hello {name}", {}, "en")).toBe("Hello {name}");
  });

  it("picks the reader's language from an API label, falling back to English", () => {
    expect(pick({ en: "Jobs", ne: "जागिर" }, "ne")).toBe("जागिर");
    expect(pick({ en: "Jobs", ne: "" }, "ne")).toBe("Jobs");
    expect(pick(null, "ne")).toBe("");
  });

  it("says how long ago, then a date", () => {
    const now = Date.parse("2026-10-26T12:00:00Z");
    expect(formatRelative("2026-10-26T11:59:40Z", "en", now)).toBe("just now");
    expect(formatRelative("2026-10-26T11:15:00Z", "en", now)).toBe("45 min ago");
    expect(formatRelative("2026-10-24T12:00:00Z", "ne", now)).toBe("२ दिन अगाडि");
    expect(formatRelative("2026-09-01T12:00:00Z", "en", now)).toMatch(/Sept?/);
    expect(formatRelative("2026-09-01T12:00:00Z", "ne", now)).toBe("१ सेप्टेम्बर");
    expect(formatDate("2026-10-26T12:00:00", "ne", { weekday: "long", day: "numeric", month: "long" })).toBe("सोमबार, २६ अक्टोबर");
  });
});

describe("forPack()", () => {
  it("uses a pack's own words where it has them, and the generic ones otherwise", () => {
    const t = translator("en");
    expect(t(forPack("applications.paste.label", "job"))).toBe("Paste a job");
    expect(t(forPack("applications.paste.label", "tender"))).toBe("Paste a tender");
    expect(t(forPack("applications.paste.label", "a_pack_added_later"))).toBe("Paste a link or text");
    expect(t(forPack("applications.paste.label", null))).toBe("Paste a link or text");
    expect(translator("ne")(forPack("opportunity.details", "grant"))).toBe("अनुदान");
  });

  it("gives every pack-specific message a generic one to fall back on", () => {
    const own = Object.keys(messages).filter((k) => /\.(job|tender|grant|contract)$/.test(k) && k.split(".").length > 2);
    expect(own.length).toBeGreaterThan(20);
    for (const key of own) {
      const generic = key.replace(/\.(job|tender|grant|contract)$/, "");
      expect(generic in messages, `${key} has no generic ${generic}`).toBe(true);
    }
  });
});
