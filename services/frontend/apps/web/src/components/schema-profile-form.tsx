"use client";

import { isApiError, type Pack, type Profile } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { cleanValue, ErrorNotice, fieldsOf, type JsonSchema, SchemaForm, toFormValue, type Value } from "@apply/kit";
import { Button, Input, Label, Textarea } from "@apply/ui";
import { type FormEvent, type ReactNode, useId, useState } from "react";

import { errorsUnder, useSchemaLabels } from "@/lib/schema-labels";

type Kind = Profile["kind"];

export interface SchemaProfileBody {
  kind: Kind;
  name: string;
  summary: string;
  tone_instructions: string;
  is_default: boolean;
  attributes: Value;
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-4 rounded-xl border bg-card p-4">
      <legend className="px-1 text-lg font-semibold">{title}</legend>
      {hint ? <p className="text-sm text-muted-foreground">{hint}</p> : null}
      {children}
    </fieldset>
  );
}

/**
 * A profile for any pack but jobs, drawn from the pack's schema: what it's called and who it's for, the facts
 * documents may use (the pack's own fields), and how documents should sound.
 */
export function SchemaProfileForm({ pack, profile, saving, error, onSubmit, formId }: {
  pack: Pack;
  profile?: Profile;
  /** Given, the page shows Save itself (a button with form={formId}), so the form has none of its own. */
  formId?: string;
  saving: boolean;
  error: unknown;
  onSubmit: (body: SchemaProfileBody) => void;
}) {
  const { t, pick, locale, error: errorText } = useI18n();
  const labels = useSchemaLabels();
  const base = useId();
  const schema = pack.profile_schema as JsonSchema;
  const fields = fieldsOf(schema);
  const [kind, setKind] = useState<Kind>(profile?.kind ?? pack.profile_kinds[0] ?? "individual");
  const [name, setName] = useState(profile?.name ?? "");
  const [summary, setSummary] = useState(profile?.summary ?? "");
  const [tone, setTone] = useState(profile?.tone_instructions ?? "");
  const [isDefault, setIsDefault] = useState(profile?.is_default ?? false);
  const [attributes, setAttributes] = useState<Value>(() => toFormValue(fields, profile?.attributes as Value | undefined));
  const fieldErrors = isApiError(error) ? error.fieldErrors : {};

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      kind, name: name.trim(), summary: summary.trim(), tone_instructions: tone.trim(), is_default: isDefault,
      attributes: cleanValue(fields, attributes),
    });
  }

  const described = (id: string, hint: boolean, message?: string) =>
    [hint ? `${id}-hint` : "", message ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined;

  return (
    <form id={formId} onSubmit={submit} className="space-y-6" noValidate>
      {error ? <ErrorNotice message={errorText(isApiError(error) ? error.code : "INTERNAL")} /> : null}

      <Section title={t("profiles.section.about")}>
        <div className="space-y-1">
          <Label htmlFor={`${base}-name`}>{t("profiles.name")}</Label>
          <p id={`${base}-name-hint`} className="text-sm text-muted-foreground">{t("profiles.name_hint")}</p>
          <Input id={`${base}-name`} value={name} onChange={(e) => setName(e.target.value)}
            aria-describedby={described(`${base}-name`, true, fieldErrors.name)} aria-invalid={fieldErrors.name ? true : undefined} />
          {fieldErrors.name ? <p id={`${base}-name-error`} className="text-sm text-destructive">{fieldErrors.name}</p> : null}
        </div>
        {pack.profile_kinds.length > 1 && !profile ? ( // chosen once, when it's made
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">{t("profiles.kind")}</legend>
            <div className="flex flex-wrap gap-2">
              {pack.profile_kinds.map((k) => (
                <label key={k} className="flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-input px-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
                  <input type="radio" name={`${base}-kind`} value={k} checked={kind === k} onChange={() => setKind(k)}
                    className="size-4 accent-[var(--primary)]" />
                  {pick(pack.profile_kind_labels[k]) || k}
                </label>
              ))}
            </div>
          </fieldset>
        ) : null}
        <div className="space-y-1">
          <Label htmlFor={`${base}-summary`}>{t("profiles.summary")}</Label>
          <p id={`${base}-summary-hint`} className="text-sm text-muted-foreground">{t("profiles.summary_hint")}</p>
          <Textarea id={`${base}-summary`} rows={3} value={summary} onChange={(e) => setSummary(e.target.value)}
            aria-describedby={`${base}-summary-hint`} />
        </div>
      </Section>

      <Section title={t("profiles.section.details")} hint={t("profiles.section.details_hint")}>
        <SchemaForm schema={schema} fields={fields} value={attributes} onChange={setAttributes} locale={locale} labels={labels}
          errors={errorsUnder(fieldErrors, "attributes")} />
      </Section>

      <Section title={t("profiles.section.writing")}>
        <div className="space-y-1">
          <Label htmlFor={`${base}-tone`}>{t("profiles.tone")}</Label>
          <p id={`${base}-tone-hint`} className="text-sm text-muted-foreground">{t("profiles.tone_hint")}</p>
          <Textarea id={`${base}-tone`} rows={2} value={tone} onChange={(e) => setTone(e.target.value)} aria-describedby={`${base}-tone-hint`} />
        </div>
        <label className="flex min-h-11 items-center gap-3 text-sm">
          <input type="checkbox" className="size-5 accent-[var(--primary)]" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
          {t("profiles.make_default")}
        </label>
      </Section>

      {formId ? null : (
        <div className="flex gap-2">
          <Button type="submit" disabled={saving || !name.trim()}>{saving ? t("action.saving") : t("action.save")}</Button>
        </div>
      )}
    </form>
  );
}
