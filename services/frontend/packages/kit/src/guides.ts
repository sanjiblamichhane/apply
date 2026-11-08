/**
 * Help guides: short Markdown pages that explain a screen. On disk each guide is a folder named after it, with
 * one file per language inside:
 *
 *   help/guides/sources/en.md
 *   help/guides/sources/ne.md
 *
 * A file opens with a front-matter block that holds its title, then the text:
 *
 *   ---
 *   title: Sources
 *   ---
 *   Where listings come from. Searches run over them (see [Searches](../searches/)).
 *
 * Guides point at each other with plain relative links to the other guide's folder, so the same link works in
 * every language and in any Markdown preview. The app follows them in place, in the reader's language.
 */

/** One guide in one language. */
export interface HelpGuide {
  title: string;
  /** The text after the front matter, as written. */
  markdown: string;
  /** The guides this one links to, by folder name, in the order they appear. */
  links: string[];
  /** Relative links that don't name a guide folder (`./notes.md`, `../x/y`), kept for {@link checkGuides}. */
  strayLinks: string[];
}

/** A guide's translations, keyed by language code. */
export type GuideTranslations = Partial<Record<string, HelpGuide>>;

/** Every guide the app ships, keyed by folder name. */
export type GuideLibrary = Record<string, GuideTranslations>;

/** The language every guide is written in first, and the one shown when a translation is missing. */
export const BASE_LANGUAGE = "en";

const FRONT_MATTER = /^---[ \t]*\n([\s\S]*?)\n---[ \t]*(?:\n|$)/;
const MARKDOWN_LINK = /\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g;
const SLUG = "[a-z0-9][a-z0-9-]*";
const GUIDE_HREF = new RegExp(`^\\.\\./(${SLUG})/?(?:[a-z]{2}\\.md)?(?:#.*)?$`);
const FILE_PATH = new RegExp(`(?:^|/)(${SLUG})/([a-z]{2})\\.md$`);

/** Whether a link points somewhere relative (another file), rather than a site, a mail address or this page. */
function isRelative(href: string): boolean {
  return !/^[a-z][a-z0-9+.-]*:/i.test(href) && !href.startsWith("/") && !href.startsWith("#");
}

/**
 * The guide a link in a guide points at, or null when it points elsewhere. Accepts the folder (`../sources/`,
 * `../sources`) and a file inside it (`../sources/en.md`); the language in a file link is ignored, since the app
 * always opens the reader's own.
 */
export function guideSlugFromHref(href: string | undefined): string | null {
  const match = href ? GUIDE_HREF.exec(href.trim()) : null;
  return match ? match[1]! : null;
}

/** Reads one guide file: its front matter's `title` and the text below it. A missing title reads as "". */
export function parseGuide(source: string): HelpGuide {
  const text = source.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n");
  const block = FRONT_MATTER.exec(text);
  const fields = new Map<string, string>();
  for (const line of block?.[1]?.split("\n") ?? []) {
    const colon = line.indexOf(":");
    if (colon <= 0) continue;
    const value = line.slice(colon + 1).trim().replace(/^(["'])(.*)\1$/, "$2");
    fields.set(line.slice(0, colon).trim(), value);
  }
  const markdown = (block ? text.slice(block[0].length) : text).trim();
  const links: string[] = [];
  const strayLinks: string[] = [];
  for (const [, href] of markdown.matchAll(MARKDOWN_LINK)) {
    const slug = guideSlugFromHref(href);
    if (slug) links.push(slug);
    else if (isRelative(href!)) strayLinks.push(href!);
  }
  return { title: fields.get("title") ?? "", markdown, links, strayLinks };
}

/**
 * Builds the library from guide files, keyed by path and holding each file's text, as a bundler's glob import
 * gives them (`{"./guides/sources/en.md": "---\ntitle: …"}`). Only the last two parts of a path count:
 * `<guide>/<language>.md`. A path of any other shape is a mistake in the app, so it throws.
 */
export function loadGuides(files: Record<string, string>): GuideLibrary {
  const library: GuideLibrary = {};
  for (const [path, source] of Object.entries(files)) {
    const match = FILE_PATH.exec(path);
    if (!match) throw new Error(`Help guide files are <guide>/<language>.md; got ${path}`);
    const [, slug, language] = match;
    (library[slug!] ??= {})[language!] = parseGuide(source);
  }
  return library;
}

/** Combines libraries, later ones adding or replacing translations of the earlier ones' guides. */
export function mergeGuides(...libraries: GuideLibrary[]): GuideLibrary {
  const merged: GuideLibrary = {};
  for (const library of libraries) {
    for (const [slug, translations] of Object.entries(library)) merged[slug] = { ...merged[slug], ...translations };
  }
  return merged;
}

/**
 * A guide in the reader's language when it's translated, otherwise in the base language. `language` says which
 * one came back, so the page can mark it (`lang`) for screen readers. Null when neither exists.
 */
export function pickTranslation(
  translations: GuideTranslations | undefined,
  locale: string,
): (HelpGuide & { language: string }) | null {
  if (!translations) return null;
  for (const language of [locale, BASE_LANGUAGE]) {
    const guide = translations[language];
    if (guide) return { ...guide, language };
  }
  return null;
}

/** Something wrong with the guides, found by {@link checkGuides}. */
export type GuideIssue =
  | { kind: "missing-translation"; slug: string; language: string }
  | { kind: "missing-title"; slug: string; language: string }
  | { kind: "empty"; slug: string; language: string }
  | { kind: "broken-link"; slug: string; language: string; href: string }
  | { kind: "no-guide"; slug: string };

/** One line per issue, for a test failure or a log. */
export function describeIssue(issue: GuideIssue): string {
  switch (issue.kind) {
    case "missing-translation": return `${issue.slug}/${issue.language}.md is missing`;
    case "missing-title": return `${issue.slug}/${issue.language}.md has no title in its front matter`;
    case "empty": return `${issue.slug}/${issue.language}.md has no text`;
    case "broken-link": return `${issue.slug}/${issue.language}.md links to ${issue.href}, which is not a guide`;
    case "no-guide": return `nothing in guides/ for "${issue.slug}"`;
  }
}

/**
 * Looks over a library for what a reader would trip on: a guide not written in one of `languages`, a file with
 * no title or no text, a relative link that doesn't reach another guide, and any slug in `expected` (the help
 * buttons the screens draw, say) with no guide behind it. Returns nothing when all is well.
 */
export function checkGuides(
  library: GuideLibrary,
  { languages, expected = [] }: { languages: readonly string[]; expected?: Iterable<string> },
): GuideIssue[] {
  const issues: GuideIssue[] = [];
  for (const slug of Object.keys(library).sort()) {
    const translations = library[slug]!;
    for (const language of languages) {
      if (!translations[language]) issues.push({ kind: "missing-translation", slug, language });
    }
    for (const [language, guide] of Object.entries(translations)) {
      if (!guide) continue;
      if (!guide.title) issues.push({ kind: "missing-title", slug, language });
      if (!guide.markdown) issues.push({ kind: "empty", slug, language });
      for (const href of guide.strayLinks) issues.push({ kind: "broken-link", slug, language, href });
      for (const target of guide.links) {
        if (!library[target]) issues.push({ kind: "broken-link", slug, language, href: `../${target}/` });
      }
    }
  }
  for (const slug of new Set(expected)) if (!library[slug]) issues.push({ kind: "no-guide", slug });
  return issues;
}
