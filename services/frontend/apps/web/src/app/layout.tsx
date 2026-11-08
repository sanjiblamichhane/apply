import "./globals.css";

import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import type { ReactNode } from "react";

import { loadLocale } from "@apply/i18n";

import { LOCALE_COOKIE, localeFrom } from "@/lib/locale";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "apply", template: "%s · apply" },
  description: "One place for everything you apply for.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f7f3" },
    { media: "(prefers-color-scheme: dark)", color: "#1b1918" },
  ],
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = localeFrom((await cookies()).get(LOCALE_COOKIE)?.value);
  // The reader's language arrives with the page, so it never flashes in English first.
  const catalogue = await loadLocale(locale);
  return (
    // suppressHydrationWarning: next-themes sets the theme class before React hydrates.
    <html lang={locale} suppressHydrationWarning>
      <body className="min-h-dvh">
        <Providers locale={locale} catalogue={catalogue}>{children}</Providers>
      </body>
    </html>
  );
}
