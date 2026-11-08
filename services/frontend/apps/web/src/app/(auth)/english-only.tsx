"use client";

import { I18nProvider } from "@apply/i18n/react";
import type { ReactNode } from "react";

export function EnglishOnly({ children }: { children: ReactNode }) {
  return <I18nProvider locale="en">{children}</I18nProvider>;
}
