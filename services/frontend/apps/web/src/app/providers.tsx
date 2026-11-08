"use client";

import { isApiError } from "@apply/api";
import { type Catalogue, loadLocale, type Locale } from "@apply/i18n";
import { I18nProvider, useI18n } from "@apply/i18n/react";
import { SonnerToaster, TooltipProvider, UiLabelsProvider } from "@apply/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ThemeProvider } from "next-themes";
import { createContext, type ReactNode, useCallback, useContext, useState } from "react";

import { writeLocaleCookie } from "@/lib/locale";

interface LocaleControl {
  setLocale: (locale: Locale) => void;
}

const LocaleControlContext = createContext<LocaleControl>({ setLocale: () => {} });

export function useLocaleControl(): LocaleControl {
  return useContext(LocaleControlContext);
}

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        refetchOnWindowFocus: true,
        // Not found, not allowed or not signed in won't change by asking again.
        retry: (failures, error) => !(isApiError(error) && [401, 403, 404, 422].includes(error.status)) && failures < 2,
      },
      mutations: { retry: false },
    },
  });
}

function TranslatedFrame({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  return (
    <UiLabelsProvider labels={{ close: t("action.close"), closeNotification: t("action.close") }}>
      {children}
      <SonnerToaster closeButton />
    </UiLabelsProvider>
  );
}

export function Providers({ locale: initial, catalogue, children }: {
  locale: Locale; catalogue: Catalogue | null; children: ReactNode;
}) {
  const [client] = useState(makeClient);
  const [locale, setLocaleState] = useState<Locale>(initial);
  const router = useRouter();

  // The next language's strings load first, so the switch is one change, never English in between.
  const setLocale = useCallback((next: Locale) => {
    writeLocaleCookie(next);
    void loadLocale(next).catch(() => null).then(() => {
      setLocaleState(next);
      document.documentElement.lang = next;
      router.refresh();
    });
  }, [router]);

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        <LocaleControlContext.Provider value={{ setLocale }}>
          <I18nProvider locale={locale} catalogue={locale === initial ? catalogue : null}>
            <TooltipProvider delayDuration={400}>
              <TranslatedFrame>{children}</TranslatedFrame>
            </TooltipProvider>
          </I18nProvider>
        </LocaleControlContext.Provider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
