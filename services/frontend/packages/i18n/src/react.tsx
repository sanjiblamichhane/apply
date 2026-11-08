"use client";

import { createContext, type ReactNode, useContext, useMemo } from "react";

import { addCatalogue, type Catalogue, errorText, formatDate, formatRelative, pick, translator, type Translate } from "./index";
import { DEFAULT_LOCALE, type Label, type Locale, type Text } from "./types";

interface I18n {
  locale: Locale;
  t: Translate;
  pick: (text: Partial<Label> | Partial<Text> | null | undefined) => string;
  error: (code: string | null | undefined) => string;
  date: (iso: string, options?: Intl.DateTimeFormatOptions) => string;
  relative: (iso: string) => string;
}

function make(locale: Locale): I18n {
  return {
    locale,
    t: translator(locale),
    pick: (text) => pick(text, locale),
    error: (code) => errorText(code, locale),
    date: (iso, options) => formatDate(iso, locale, options),
    relative: (iso) => formatRelative(iso, locale),
  };
}

const I18nContext = createContext<I18n>(make(DEFAULT_LOCALE));

/**
 * The reader's language for everything inside. A language other than English or Nepali needs its catalogue: pass
 * it here (as the web app's server does), or `await loadLocale(locale)` before switching; otherwise it reads in
 * English.
 */
export function I18nProvider({ locale, catalogue, children }: { locale: Locale; catalogue?: Catalogue | null; children: ReactNode }) {
  if (catalogue) addCatalogue(locale, catalogue);
  const value = useMemo(() => make(locale), [locale, catalogue]); // eslint-disable-line react-hooks/exhaustive-deps
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  return useContext(I18nContext);
}
