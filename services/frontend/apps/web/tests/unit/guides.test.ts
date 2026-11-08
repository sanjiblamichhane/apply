// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";

import { allMessages, type Locale, LOCALES, loadLocale } from "@apply/i18n";
import { checkGuides, describeIssue, loadGuides, pickTranslation } from "@apply/kit";
import { describe, expect, it } from "vitest";

import { ENGLISH_GUIDES, loadGuidesFor } from "@/help/guides";

// The guide folders as they sit on disk, and anything in them that isn't a guide file.
const root = new URL("../../src/help/guides/", import.meta.url);
const files: Record<string, string> = {};
const strays: string[] = [];
for (const folder of readdirSync(root, { withFileTypes: true })) {
  if (!folder.isDirectory()) {
    strays.push(folder.name);
    continue;
  }
  for (const name of readdirSync(new URL(`${folder.name}/`, root))) {
    const language = name.replace(/\.md$/, "");
    if (name.endsWith(".md") && (LOCALES as readonly string[]).includes(language)) {
      files[`${folder.name}/${name}`] = readFileSync(new URL(`${folder.name}/${name}`, root), "utf8");
    } else {
      strays.push(`${folder.name}/${name}`);
    }
  }
}
const library = loadGuides(files);

// The slug of every "?" in the app's source.
function sourceFiles(dir: URL): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (entry.isDirectory()) return sourceFiles(new URL(`${entry.name}/`, dir));
    return /\.tsx?$/.test(entry.name) ? [readFileSync(new URL(entry.name, dir), "utf8")] : [];
  });
}
const source = sourceFiles(new URL("../../src/", import.meta.url)).join("\n");
const helpSlugs = [...source.matchAll(/<Help(?:Button)? slug="([a-z-]+)"/g)].map((match) => match[1]!);

// What the screens say, per language. A **bold** phrase in a guide names something on screen, so it must match.
await Promise.all(LOCALES.map((locale) => loadLocale(locale)));
const END_PUNCTUATION = /[:.…։।。：]$/u;
const screenWords = (locale: Locale) => new Set(Object.values(allMessages(locale)).map((text) => text.replace(END_PUNCTUATION, "")));
// Bold used for emphasis or a name rather than a label, per language.
const EMPHASIS: Record<string, string[]> = JSON.parse(readFileSync(new URL("./guide-emphasis.json", import.meta.url), "utf8"));

describe("help guides", () => {
  it("hold only <guide>/<language>.md files", () => {
    expect(strays).toEqual([]);
  });

  it("are complete: every language, a title and text, working links, and a guide for every ?", () => {
    expect(helpSlugs.length).toBeGreaterThan(10);
    expect(checkGuides(library, { languages: LOCALES, expected: helpSlugs }).map(describeIssue)).toEqual([]);
  });

  it("are all bundled, in each language", async () => {
    expect(Object.keys(ENGLISH_GUIDES).sort()).toEqual(Object.keys(library).sort());
    for (const locale of LOCALES) {
      const loaded = await loadGuidesFor(locale);
      for (const slug of Object.keys(library)) {
        expect(pickTranslation(loaded[slug], locale)?.title, `${slug}/${locale}.md`).toBe(library[slug]?.[locale]?.title);
      }
    }
  });

  it("name buttons and places exactly as the screens show them", () => {
    const mismatched: string[] = [];
    for (const [slug, translations] of Object.entries(library)) {
      for (const [language, guide] of Object.entries(translations)) {
        const words = screenWords(language as Locale);
        const emphasis = new Set(EMPHASIS[language] ?? []);
        for (const [, bold] of guide!.markdown.matchAll(/\*\*([^*]+)\*\*/g)) {
          const steps = bold!.split(/\s+[→←]\s+/);
          if (!emphasis.has(bold!) && !steps.every((step) => words.has(step.replace(END_PUNCTUATION, "")))) {
            mismatched.push(`${slug}/${language}.md: ${bold}`);
          }
        }
      }
    }
    expect(mismatched).toEqual([]);
  });
});
