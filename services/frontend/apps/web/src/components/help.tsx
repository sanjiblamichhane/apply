"use client";

import { useI18n } from "@apply/i18n/react";
import { type GuideLibrary, HelpButton, HelpProvider, type MarkdownComponent } from "@apply/kit";
import { type ReactNode, useEffect, useState } from "react";

import { ENGLISH_GUIDES, loadGuidesFor } from "@/help/guides";

import { SafeMarkdown } from "./safe-markdown";

/** Gives every signed-in page the help guides (src/help), switching to the reader's language once it loads. */
export function Guides({ children }: { children: ReactNode }) {
  const { t, locale } = useI18n();
  const [library, setLibrary] = useState<GuideLibrary>(ENGLISH_GUIDES);
  useEffect(() => {
    let current = true;
    // If the translation can't be fetched, the English guides stay up.
    void loadGuidesFor(locale).then((loaded) => { if (current) setLibrary(loaded); }, () => {});
    return () => { current = false; };
  }, [locale]);
  return (
    <HelpProvider library={library} locale={locale} Markdown={SafeMarkdown as MarkdownComponent}
      labels={{ panel: t("help.panel"), help: (title) => t("help.button", { title }), close: t("action.close") }}>
      {children}
    </HelpProvider>
  );
}

/** The "?" that opens a guide: beside a page's title (PageHeader's ``help``) or a part's heading. */
export function Help({ slug, className }: { slug: string; className?: string }) {
  const { t } = useI18n();
  return <HelpButton slug={slug} className={className} labels={{ help: (title) => t("help.button", { title }) }} />;
}
