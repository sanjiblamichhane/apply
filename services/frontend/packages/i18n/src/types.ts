/**
 * The languages apply speaks: English, Nepali and Spanish. English and Nepali are written inline next to each key
 * (messages/*.ts); every other language is a catalogue, locales/<code>.json, loaded when a reader picks it. Adding a
 * language: a line here, the same in services/backend/src/apply/i18n.py, its two catalogues and its guides (the
 * tests list what's missing).
 */
export interface LanguageInfo {
  /** The language named in itself, as the picker shows it. */
  name: string;
  /** In English, for docs and for people helping someone choose. */
  english: string;
  /** The BCP 47 tag `Intl` formats numbers and dates with. */
  intl: string;
}

export const LANGUAGES = {
  en: { name: "English", english: "English", intl: "en-GB" },
  ne: { name: "नेपाली", english: "Nepali", intl: "ne-NP" },
  es: { name: "Español", english: "Spanish", intl: "es" },
} as const satisfies Record<string, LanguageInfo>;

export type Locale = keyof typeof LANGUAGES;
export const LOCALES = Object.keys(LANGUAGES) as Locale[];
export const DEFAULT_LOCALE: Locale = "en";

/** The languages written inline in messages/*.ts; the rest come from locales/<code>.json. */
export type InlineLocale = "en" | "ne";

/**
 * One string, as written in the source: English and Nepali. Every message has this shape; the other languages are
 * in their catalogues.
 */
export interface Text {
  en: string;
  ne: string;
}

/**
 * A label the API sends: English always, and each other language it has (a label stored before a language was
 * added has only English and Nepali, and reads in English there).
 */
export type Label = { en: string } & Partial<Record<Locale, string | null>>;

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && Object.hasOwn(LANGUAGES, value);
}

export function languageOf(locale: Locale): LanguageInfo {
  return LANGUAGES[locale];
}

/**
 * The best of apply's languages for a browser's preferences (`navigator.languages`, or an Accept-Language
 * header's tags in order): "es-MX" → es, "ne-NP" → ne, else English.
 */
export function bestLocale(preferred: readonly string[]): Locale {
  for (const tag of preferred) {
    const base = tag.trim().toLowerCase().split(/[-_;]/)[0];
    if (isLocale(base)) return base;
  }
  return DEFAULT_LOCALE;
}
