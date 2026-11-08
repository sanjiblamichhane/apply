"use client";

import { isApiError, type Profile } from "@apply/api";
import type { MessageKey } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label, Textarea } from "@apply/ui";
import { Add, Trash } from "@apply/ui/icons";
import { type FormEvent, type ReactNode, useId, useState } from "react";

import { emptyEducation, emptyExperience, emptyForm, formField, type ProfileForm as Form, toBody, toForm } from "@/lib/profile-form";

/** One field: its label, an optional hint, the control, and its error, tied together for assistive tech. */
function Field({ label, hint, error, children, id }: {
  label: string; hint?: string; error?: string; id: string;
  children: (props: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => ReactNode;
}) {
  const described = [hint ? `${id}-hint` : "", error ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined;
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      {hint ? <p id={`${id}-hint`} className="text-sm text-muted-foreground">{hint}</p> : null}
      {children({ id, "aria-describedby": described, "aria-invalid": error ? true : undefined })}
      {error ? <p id={`${id}-error`} className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-4 rounded-xl border bg-card p-4">
      <legend className="px-1 text-lg font-semibold">{title}</legend>
      {children}
    </fieldset>
  );
}

export function ProfileForm({ profile, saving, error, onSubmit, formId }: {
  profile?: Profile;
  /** Given, the page shows Save itself (a button with form={formId}), so the form has none of its own. */
  formId?: string;
  saving: boolean;
  error: unknown;
  onSubmit: (body: ReturnType<typeof toBody>) => void;
}) {
  const { t, error: errorText } = useI18n();
  const base = useId();
  const [form, setForm] = useState<Form>(() => (profile ? toForm(profile) : emptyForm()));
  const fieldErrors = Object.fromEntries(Object.entries(isApiError(error) ? error.fieldErrors : {})
    .map(([loc, msg]) => [formField(loc), msg]));
  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => ({ ...f, [key]: value }));
  const text = (key: keyof Form, label: MessageKey, opts: { hint?: MessageKey; type?: string; autoComplete?: string; multiline?: number } = {}) => (
    <Field id={`${base}-${key}`} label={t(label)} hint={opts.hint ? t(opts.hint) : undefined} error={fieldErrors[key]}>
      {(props) => opts.multiline ? (
        <Textarea {...props} rows={opts.multiline} value={form[key] as string} onChange={(e) => set(key, e.target.value as never)} />
      ) : (
        <Input {...props} type={opts.type ?? "text"} autoComplete={opts.autoComplete} value={form[key] as string}
          onChange={(e) => set(key, e.target.value as never)} />
      )}
    </Field>
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit(toBody(form));
  }

  return (
    <form id={formId} onSubmit={submit} className="space-y-6" noValidate>
      {error ? <ErrorNotice message={errorText(isApiError(error) ? error.code : "INTERNAL")} /> : null}

      <Section title={t("profiles.section.about")}>
        {text("name", "profiles.name", { hint: "profiles.name_hint" })}
        {text("summary", "profiles.summary", { hint: "profiles.summary_hint", multiline: 3 })}
      </Section>

      <Section title={t("profiles.section.contact")}>
        <div className="grid gap-4 sm:grid-cols-2">
          {text("full_name", "profiles.full_name", { autoComplete: "name" })}
          {text("email", "profiles.email", { type: "email", autoComplete: "email" })}
          {text("phone", "profiles.phone", { type: "tel", autoComplete: "tel" })}
          {text("location", "profiles.location", { autoComplete: "address-level2" })}
        </div>
        <fieldset className="space-y-3">
          <legend className="text-sm font-medium">{t("profiles.links")}</legend>
          {form.links.map((link, i) => (
            <div key={i} className="grid items-end gap-2 sm:grid-cols-[1fr_2fr_auto]">
              <Field id={`${base}-link-${i}-label`} label={t("profiles.link_label")}>
                {(props) => <Input {...props} value={link.label} onChange={(e) => set("links", form.links.map((l, j) => j === i ? { ...l, label: e.target.value } : l))} />}
              </Field>
              <Field id={`${base}-link-${i}-url`} label={t("profiles.link_url")} error={fieldErrors[`links.${i}.url`]}>
                {(props) => <Input {...props} type="url" value={link.url} onChange={(e) => set("links", form.links.map((l, j) => j === i ? { ...l, url: e.target.value } : l))} />}
              </Field>
              <Button type="button" variant="ghost" size="icon" aria-label={`${t("action.remove")}: ${link.label || link.url}`}
                onClick={() => set("links", form.links.filter((_, j) => j !== i))}><Trash aria-hidden /></Button>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => set("links", [...form.links, { label: "", url: "" }])}>
            <Add aria-hidden />{t("profiles.add_link")}
          </Button>
        </fieldset>
      </Section>

      <Section title={t("profiles.section.experience")}>
        {form.experience.map((role, i) => (
          <fieldset key={i} className="space-y-3 rounded-lg border p-3">
            <legend className="px-1 text-sm font-semibold">{t("profiles.role_n", { n: i + 1 })}</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {(["title", "organisation", "start", "end", "location"] as const).map((key) => (
                <Field key={key} id={`${base}-exp-${i}-${key}`} label={t(`profiles.experience.${key}`)}
                  hint={key === "end" ? t("profiles.experience.end_hint") : undefined} error={fieldErrors[`experience.${i}.${key}`]}>
                  {(props) => <Input {...props} value={role[key]} onChange={(e) => set("experience", form.experience.map((r, j) => j === i ? { ...r, [key]: e.target.value } : r))} />}
                </Field>
              ))}
            </div>
            <Field id={`${base}-exp-${i}-highlights`} label={t("profiles.experience.highlights")} hint={t("profiles.experience.highlights_hint")}>
              {(props) => <Textarea {...props} rows={4} value={role.highlights} onChange={(e) => set("experience", form.experience.map((r, j) => j === i ? { ...r, highlights: e.target.value } : r))} />}
            </Field>
            <Button type="button" variant="ghost" size="sm" className="gap-2" onClick={() => set("experience", form.experience.filter((_, j) => j !== i))}>
              <Trash aria-hidden />{t("profiles.remove_experience")}
            </Button>
          </fieldset>
        ))}
        <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => set("experience", [...form.experience, emptyExperience()])}>
          <Add aria-hidden />{t("profiles.add_experience")}
        </Button>
      </Section>

      <Section title={t("profiles.section.education")}>
        {form.education.map((item, i) => (
          <fieldset key={i} className="space-y-3 rounded-lg border p-3">
            <legend className="px-1 text-sm font-semibold">{t("profiles.qualification_n", { n: i + 1 })}</legend>
            <div className="grid gap-3 sm:grid-cols-3">
              {(["qualification", "institution", "year"] as const).map((key) => (
                <Field key={key} id={`${base}-edu-${i}-${key}`} label={t(`profiles.education.${key}`)} error={fieldErrors[`education.${i}.${key}`]}>
                  {(props) => <Input {...props} value={item[key]} onChange={(e) => set("education", form.education.map((r, j) => j === i ? { ...r, [key]: e.target.value } : r))} />}
                </Field>
              ))}
            </div>
            <Button type="button" variant="ghost" size="sm" className="gap-2" onClick={() => set("education", form.education.filter((_, j) => j !== i))}>
              <Trash aria-hidden />{t("profiles.remove_education")}
            </Button>
          </fieldset>
        ))}
        <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => set("education", [...form.education, emptyEducation()])}>
          <Add aria-hidden />{t("profiles.add_education")}
        </Button>
      </Section>

      <Section title={t("profiles.section.skills")}>
        {text("skills", "profiles.skills", { hint: "profiles.skills_hint", multiline: 5 })}
        <div className="grid gap-4 sm:grid-cols-2">
          {text("languages", "profiles.languages", { hint: "profiles.skills_hint", multiline: 3 })}
          {text("certifications", "profiles.certifications", { hint: "profiles.skills_hint", multiline: 3 })}
        </div>
        {text("work_authorization", "profiles.work_authorization", { hint: "profiles.work_authorization_hint" })}
      </Section>

      <Section title={t("profiles.section.writing")}>
        {text("tone_instructions", "profiles.tone", { hint: "profiles.tone_hint", multiline: 2 })}
        <label className="flex min-h-11 items-center gap-3 text-sm">
          <input type="checkbox" className="size-5 accent-[var(--primary)]" checked={form.is_default}
            onChange={(e) => set("is_default", e.target.checked)} />
          {t("profiles.make_default")}
        </label>
      </Section>

      {formId ? null : (
        <div className="flex gap-2">
          <Button type="submit" disabled={saving || !form.name.trim()}>{saving ? t("action.saving") : t("action.save")}</Button>
        </div>
      )}
    </form>
  );
}
