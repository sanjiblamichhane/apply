import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  bestLocale, CATALOGUE_LOADERS, errors, errorText, formatDate, formatNumber, hasCatalogue, LANGUAGES, loadLocale,
  type Locale, LOCALES, messages, translator,
} from "../src";

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
const english: Record<string, string> = {
  ...Object.fromEntries(Object.entries(messages).map(([k, v]) => [k, v.en])),
  ...Object.fromEntries(Object.entries(errors).map(([k, v]) => [`error.${k}`, v.en])),
};
// The script a language is written in, where it isn't Latin (a Latin-script one is checked for being mostly not
// English instead). Add a language's here with its catalogue.
const SCRIPT: Partial<Record<Locale, RegExp>> = {};
// Kept as in English on purpose: the product's name, the languages' own names, codes.
const SAME_IN_ALL = new Set(["app.name", "language.en", "language.ne", "review.pdf", "profiles.form.item"]);
const catalogued = LOCALES.filter((l) => l !== "en" && l !== "ne") as Exclude<Locale, "en" | "ne">[];

describe("every language's catalogue", () => {
  it("is listed for loading, and nothing else is", () => {
    expect(Object.keys(CATALOGUE_LOADERS).sort()).toEqual([...catalogued].sort());
  });

  for (const locale of catalogued) {
    it(`${locale} (${LANGUAGES[locale].english}) has every message, with the English placeholders, in its script`, async () => {
      const catalogue = (await CATALOGUE_LOADERS[locale]()).default;
      const problems: string[] = [];
      let same = 0;
      for (const [key, en] of Object.entries(english)) {
        const text = catalogue[key];
        if (typeof text !== "string" || !text.trim()) { problems.push(`${key}: missing`); continue; }
        if (placeholders(text).join() !== placeholders(en).join()) problems.push(`${key}: placeholders differ`);
        if (SAME_IN_ALL.has(key)) continue;
        if (text === en) same++;
        else if (SCRIPT[locale] && !SCRIPT[locale]!.test(text)) problems.push(`${key}: not in its script`);
      }
      for (const key of Object.keys(catalogue)) if (!(key in english)) problems.push(`${key}: no such message`);
      expect(problems).toEqual([]);
      expect(same / Object.keys(english).length, "too much left in English").toBeLessThan(0.12);
    });
  }
});

describe("languages", () => {
  it("are the same list as the backend's", () => {
    const python = readFileSync(new URL("../../../../backend/src/apply/i18n.py", import.meta.url), "utf8");
    const literal = /Locale = Literal\[([^\]]+)\]/.exec(python)![1]!;
    const backend = [...literal.matchAll(/"([a-z]{2})"/g)].map((m) => m[1]);
    expect([...backend].sort()).toEqual([...LOCALES].sort());
  });

  it("are English, Nepali and Spanish, each named in itself", () => {
    expect(LOCALES).toEqual(["en", "ne", "es"]);
    expect(LOCALES.map((l) => LANGUAGES[l].name)).toEqual(["English", "नेपाली", "Español"]);
  });

  it("match a browser's preferences", () => {
    expect(bestLocale(["es-MX", "en"])).toBe("es");
    expect(bestLocale(["fr-FR", "ne-NP"])).toBe("ne");
    expect(bestLocale(["es_419"])).toBe("es");
    expect(bestLocale(["xx", "kl"])).toBe("en");
  });
});

describe("a catalogue language", () => {
  it("reads in English until its catalogue is loaded, then in itself", async () => {
    const before = hasCatalogue("es");
    if (!before) expect(translator("es")("action.save")).toBe("Save");
    await loadLocale("es");
    expect(hasCatalogue("es")).toBe(true);
    expect(translator("es")("action.save")).not.toBe("Save");
    expect(errorText("NETWORK", "es")).not.toBe(errorText("NETWORK", "en"));
  });

  it("writes numbers and dates as its readers do", async () => {
    await loadLocale("es");
    expect(formatNumber(12345.5, "es")).toBe("12.345,5");
    expect(translator("es")("applications.count", { count: 12345 })).toContain("12.345");
    expect(formatDate("2026-10-26T12:00:00", "es", { day: "numeric", month: "long" })).toBe("26 de octubre");
    expect(formatNumber(1234, "ne")).toBe("१,२३४");
  });
});
