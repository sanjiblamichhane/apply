import type { Locale } from "@apply/i18n";
import { type GuideLibrary, loadGuides, mergeGuides } from "@apply/kit";

import { texts } from "./texts";

/**
 * The help guides shipped with the app. Each guide is a folder under `guides/` named after the slug a screen's
 * "?" uses (`<Help slug="sources" />`), holding `en.md`, `ne.md` and `es.md`. Each file starts with front matter
 * (`title: …`); link to another guide by its folder, `[Searches](../searches/)`.
 *
 * Files are gathered with `import.meta.glob` and the `?raw` query: next.config.ts has Turbopack load `*.md?raw` as
 * text, and Vitest does that on its own. English ships with the page. Each other language is a module in
 * `translations/`, fetched with import() only when a reader picks it, so its text is a separate chunk.
 * tests/unit/guides.test.ts checks that every guide is complete.
 */
type Files = Record<string, string>;

const english: Files = texts(import.meta.glob<{ default: string }>("./guides/*/en.md", { query: "?raw", eager: true }));

const translations: Record<Exclude<Locale, "en">, () => Promise<{ default: Files }>> = {
  ne: () => import("./translations/ne"),
  es: () => import("./translations/es"),
};

/** Every guide in English, ready from the first render. */
export const ENGLISH_GUIDES: GuideLibrary = loadGuides(english);

/** Every guide in the reader's language, with English standing in for any not translated yet. */
export async function loadGuidesFor(locale: Locale): Promise<GuideLibrary> {
  if (locale === "en") return ENGLISH_GUIDES;
  return mergeGuides(ENGLISH_GUIDES, loadGuides((await translations[locale]()).default));
}
