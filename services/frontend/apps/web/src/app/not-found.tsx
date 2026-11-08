"use client";

import { useI18n } from "@apply/i18n/react";
import { Button } from "@apply/ui";
import Link from "next/link";

export default function NotFound() {
  const { t } = useI18n();
  return (
    <main id="main" className="grid min-h-dvh place-items-center px-4">
      <div className="max-w-md space-y-3 text-center">
        <h1 className="text-2xl font-semibold">{t("shell.not_found")}</h1>
        <p className="text-muted-foreground">{t("shell.not_found_body")}</p>
        <Button asChild><Link href="/applications">{t("shell.go_home")}</Link></Button>
      </div>
    </main>
  );
}
