/**
 * Every string the web app shows, in each of apply's languages (types.ts lists them).
 *
 *   const t = translator("ne");
 *   t("applications.count", { count: 3 })     // "३ आवेदन"
 *   pick({ en: "Jobs", ne: "जागिर" }, "ne")   // labels the API sends
 *   errorText("LLM_UNREACHABLE", "en")        // what an API error code means
 *
 * English and Nepali are always here. Another language's catalogue is loaded first (`await loadLocale("es")`, or
 * handed over with `addCatalogue`, as the web app's server does); until then its reader sees English.
 * Numbers in a message are written as the reader writes them (Devanagari digits for Nepali, "12.345,5" in Spanish).
 */

import { common } from "./messages/common";
import { type ErrorKey, errors } from "./messages/errors";
import {
  application,
  applications,
  automatic,
  auth,
  discovery,
  documents,
  extension,
  opportunity,
  profiles,
  reviewing,
  settings,
} from "./messages/screens";
import { CATALOGUE_LOADERS } from "./locales";
import { type InlineLocale, type Label, LANGUAGES, type Locale, type Text } from "./types";

export * from "./types";
export { CATALOGUE_LOADERS } from "./locales";
export { errors } from "./messages/errors";
export type { ErrorKey } from "./messages/errors";

export const messages = {
  ...common,
  ...auth,
  ...applications,
  ...opportunity,
  ...application,
  ...documents,
  ...profiles,
  ...settings,
  ...discovery,
  ...reviewing,
  ...extension,
  ...automatic,
} as const satisfies Record<string, Text>;

export type MessageKey = keyof typeof messages;

/**
 * A message in a pack's own words where it has them ("applications.paste.label.tender"), otherwise the generic
 * one: a pack added later reads sensibly with no new strings.
 */
export function forPack(key: MessageKey, pack: string | null | undefined): MessageKey {
  const own = `${key}.${pack}`;
  return pack && own in messages ? (own as MessageKey) : key;
}
export type Vars = Record<string, string | number>;
export type Translate = (key: MessageKey, vars?: Vars) => string;

/** A language's strings: every message key, and `error.<CODE>` for each error. */
export type Catalogue = Record<string, string>;

const inline = (locale: Locale): locale is InlineLocale => locale === "en" || locale === "ne";
const catalogues = new Map<Locale, Catalogue>();

/** Make a language's strings available (the web app's server reads them and hands them to the page). */
export function addCatalogue(locale: Locale, catalogue: Catalogue): void {
  if (!inline(locale)) catalogues.set(locale, catalogue);
}

/** Whether a language can be shown now, without loading. */
export function hasCatalogue(locale: Locale): boolean {
  return inline(locale) || catalogues.has(locale);
}

/** Load a language's catalogue (once), then return it; English and Nepali need none. */
export async function loadLocale(locale: Locale): Promise<Catalogue | null> {
  if (inline(locale)) return null;
  const have = catalogues.get(locale);
  if (have) return have;
  const loaded = (await CATALOGUE_LOADERS[locale]()).default as Catalogue;
  catalogues.set(locale, loaded);
  return loaded;
}

/** A message's text in a language, or undefined if that language doesn't have it (yet). */
function textOf(key: string, locale: Locale): string | undefined {
  if (inline(locale)) {
    const entry = (messages as Record<string, Text>)[key];
    if (entry) return entry[locale] || undefined;
    if (key.startsWith("error.")) return (errors as Record<string, Text>)[key.slice(6)]?.[locale] || undefined;
    return undefined;
  }
  return catalogues.get(locale)?.[key] || undefined;
}

/** Every message in a language, unfilled (for checks such as "a guide names buttons as the screens do"). */
export function allMessages(locale: Locale): Record<MessageKey, string> {
  return Object.fromEntries(Object.keys(messages).map((key) => [key, textOf(key, locale) ?? messages[key as MessageKey].en])) as Record<MessageKey, string>;
}
const DEVANAGARI_DIGITS = "०१२३४५६७८९";
// The Gregorian months as Nepali writes them. Browsers' locale data for Nepali varies (some have none), so
// apply says them itself rather than fall back to English mid-sentence.
const NE_WEEKDAYS = ["आइतबार", "सोमबार", "मङ्गलबार", "बुधबार", "बिहीबार", "शुक्रबार", "शनिबार"];
const NE_MONTHS = ["जनवरी", "फेब्रुअरी", "मार्च", "अप्रिल", "मे", "जुन", "जुलाई", "अगस्ट", "सेप्टेम्बर", "अक्टोबर",
  "नोभेम्बर", "डिसेम्बर"];

export function intlLocale(locale: Locale): string {
  return LANGUAGES[locale].intl;
}

/** Digits in the reader's script for Nepali (Devanagari), whatever the browser's locale data says. */
export function localDigits(text: string, locale: Locale): string {
  return locale === "ne" ? text.replace(/[0-9]/g, (d) => DEVANAGARI_DIGITS[Number(d)]!) : text;
}

/** A number as the reader writes it: their digits and separators ("12,345.5", "12.345,5", "१२,३४५.५"). */
export function formatNumber(value: number, locale: Locale): string {
  if (locale === "ne") return localDigits(new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 }).format(value), "ne");
  return new Intl.NumberFormat(intlLocale(locale), { maximumFractionDigits: 2 }).format(value);
}

export function fill(template: string, vars: Vars | undefined, locale: Locale): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => {
    const value = vars[name];
    if (value === undefined) return whole;
    return typeof value === "number" ? formatNumber(value, locale) : value;
  });
}

export function translator(locale: Locale): Translate {
  return (key, vars) => {
    const text = textOf(key, locale) ?? messages[key]?.en;
    if (text === undefined) return key;
    return fill(text, vars, locale);
  };
}

/** A label the API sends ({en, ne, es, …}), in the reader's language, else English. */
export function pick(text: Partial<Label> | Partial<Text> | null | undefined, locale: Locale): string {
  if (!text) return "";
  return (text as Partial<Label>)[locale] || text.en || "";
}

export function errorText(code: string | null | undefined, locale: Locale): string {
  const key = code && code in errors ? code : "INTERNAL";
  return textOf(`error.${key}`, locale) ?? (errors[key as ErrorKey] as Text).en;
}

export function formatDate(iso: string | Date, locale: Locale, options?: Intl.DateTimeFormatOptions): string {
  const date = typeof iso === "string" ? new Date(iso) : iso;
  const wanted = options ?? { day: "numeric", month: "short", year: "numeric" };
  if (locale !== "ne") return new Intl.DateTimeFormat(intlLocale(locale), wanted).format(date);
  const parts: string[] = [];
  if (wanted.weekday) parts.push(`${NE_WEEKDAYS[date.getDay()]},`);
  if (wanted.day) parts.push(String(date.getDate()));
  if (wanted.month) parts.push(NE_MONTHS[date.getMonth()]!);
  if (wanted.year) parts.push(String(date.getFullYear()));
  let text = parts.join(" ");
  if (wanted.hour) {
    text += ` ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  }
  return localDigits(text, "ne");
}

/** "3 min ago", "2 d ago", then a date. ``now`` is injectable for tests. */
export function formatRelative(iso: string, locale: Locale, now: number = Date.now()): string {
  const t = translator(locale);
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const minutes = Math.floor((now - then) / 60_000);
  if (minutes < 1) return t("time.just_now");
  if (minutes < 60) return t("time.minutes_ago", { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("time.hours_ago", { count: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return t("time.days_ago", { count: days });
  return formatDate(iso, locale, { day: "numeric", month: "short" });
}
