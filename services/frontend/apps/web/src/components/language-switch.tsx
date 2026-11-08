"use client";

import { LANGUAGES, LOCALES, type Locale } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { useId, useState } from "react";

import { useLocaleControl } from "@/app/providers";
import { useUpdateMe } from "@/lib/queries";

/**
 * apply's languages as radio buttons: each named in itself, with its own `lang`, so a reader who doesn't read the
 * current one can still find theirs. Signed in, the account remembers it too.
 */
export function LanguageSwitch({ signedIn = false }: { signedIn?: boolean }) {
  const { t, locale } = useI18n();
  const { setLocale } = useLocaleControl();
  const updateMe = useUpdateMe();
  const name = useId();
  // The choice shows at once; the screens follow as soon as its language has loaded.
  const [chosen, setChosen] = useState(locale);
  const [shown, setShown] = useState(locale);
  if (shown !== locale) {
    setShown(locale);
    setChosen(locale);
  }

  function choose(next: Locale) {
    setChosen(next);
    setLocale(next);
    if (signedIn) {
      updateMe.mutate({ locale: next });
    }
  }

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{t("shell.language")}</legend>
      <div className="flex flex-wrap gap-2">
        {LOCALES.map((option) => (
          <label key={option} lang={option}
            className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
            <input type="radio" name={name} value={option} checked={chosen === option} onChange={() => choose(option)}
              className="size-4 accent-[var(--primary)]" />
            {LANGUAGES[option].name}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
