"use client";

import { useI18n } from "@apply/i18n/react";
import type { SchemaFormLabels, Value } from "@apply/kit";

/** Jobs keep their tailored screens (profile form, posting fields); every other pack is drawn from its schema. */
export const TAILORED_PACK = "job";

/** The schema form's words, in the reader's language. */
export function useSchemaLabels(): SchemaFormLabels {
  const { t } = useI18n();
  return {
    add: (label) => t("profiles.form.add", { label }),
    remove: (label, n) => t("profiles.form.remove", { label, n }),
    item: (label, n) => t("profiles.form.item", { label, n }),
    onePerLine: t("profiles.skills_hint"),
  };
}

/** The API's field errors for one object ("attributes.team.0.name"), keyed as the schema form expects ("team.0.name"). */
export function errorsUnder(fieldErrors: Record<string, string>, prefix: string): Record<string, string> {
  return Object.fromEntries(Object.entries(fieldErrors)
    .filter(([loc]) => loc.startsWith(`${prefix}.`))
    .map(([loc, message]) => [loc.slice(prefix.length + 1), message]));
}

export type { Value };
