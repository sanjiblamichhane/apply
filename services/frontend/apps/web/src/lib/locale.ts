import { DEFAULT_LOCALE, isLocale, type Locale } from "@apply/i18n";

/** The reader's language lives in this cookie (so the first paint is right, signed in or not) and on the account. */
export const LOCALE_COOKIE = "apply_locale";

export function localeFrom(value: string | undefined | null): Locale {
  return isLocale(value) ? value : DEFAULT_LOCALE;
}

/** The language this browser chose (in Settings), or null while it's still on the default. */
export function readLocaleCookie(cookies: string = document.cookie): Locale | null {
  const found = cookies.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${LOCALE_COOKIE}=`));
  const value = found?.slice(LOCALE_COOKIE.length + 1);
  return isLocale(value) ? value : null;
}

export function writeLocaleCookie(locale: Locale): void {
  document.cookie = `${LOCALE_COOKIE}=${locale}; Path=/; Max-Age=31536000; SameSite=Lax`;
}
