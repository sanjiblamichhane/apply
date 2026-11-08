"use client";

import { isApiError, type Opportunity } from "@apply/api";
import { forPack, type MessageKey } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { cleanValue, ErrorNotice, fieldsOf, type JsonSchema, SchemaForm, SchemaView, toFormValue, type Value } from "@apply/kit";
import { Button, Input, Label, Textarea } from "@apply/ui";
import { Edit, Information, InProgress, Renew } from "@apply/ui/icons";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import { SafeMarkdown } from "@/components/safe-markdown";
import { useExtractAgain, usePack, useUpdateOpportunity } from "@/lib/queries";
import { errorsUnder, TAILORED_PACK, useSchemaLabels } from "@/lib/schema-labels";

const FIELDS = ["job_title", "company_name", "location", "employment_type", "salary_text", "visa_sponsorship_text",
  "hiring_manager"] as const;
type Field = (typeof FIELDS)[number];
const WORKPLACES = ["", "onsite", "hybrid", "remote"] as const;

function attr(opp: Opportunity, key: string): string {
  const value = (opp.attributes as Record<string, unknown>)[key];
  return typeof value === "string" ? value : "";
}

/** What's apply for, as read from the notice (or filled in by the person), with a way to correct it. */
export function OpportunityPanel({ opportunity }: { opportunity: Opportunity }) {
  const { t, error } = useI18n();
  const tailored = opportunity.pack === TAILORED_PACK;
  const schema = usePack(opportunity.pack).data?.opportunity_schema as JsonSchema | undefined;
  const extraction = opportunity.extraction;
  const [editing, setEditing] = useState(false);
  const extractAgain = useExtractAgain(opportunity.id);
  const manual = extraction.status === "manual" && !extraction.edited && !opportunity.title;

  return (
    <section aria-labelledby="job-heading" className="space-y-4 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1"><h2 id="job-heading" className="text-lg font-semibold">{t(forPack("opportunity.details", opportunity.pack))}</h2><Help slug="opportunity" /></div>
        {!editing && extraction.status !== "pending" ? (
          <Button variant="outline" size="sm" className="gap-2" onClick={() => setEditing(true)}>
            <Edit aria-hidden />{t("opportunity.edit")}
          </Button>
        ) : null}
      </div>

      {extraction.status === "pending" ? (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <InProgress className="size-4 animate-spin" aria-hidden />{t(forPack("opportunity.reading", opportunity.pack))}
        </p>
      ) : null}

      {manual && !editing ? (
        <div className="space-y-3 rounded-lg border border-input p-3">
          <p className="flex items-start gap-2 text-sm">
            <Information className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span><strong>{t("opportunity.manual.title")}.</strong> {t(forPack("opportunity.manual.body", opportunity.pack))}</span>
          </p>
          {extraction.error_code ? <p className="text-sm text-muted-foreground">{error(extraction.error_code)}</p> : null}
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => setEditing(true)}>{t("opportunity.manual.title")}</Button>
            {extraction.method !== "manual" || extraction.error_code === "EXTRACT_FAILED" || extraction.error_code?.startsWith("LLM_") ? (
              <Button size="sm" variant="outline" className="gap-2" disabled={extractAgain.isPending}
                onClick={() => extractAgain.mutate()}>
                <Renew aria-hidden />{t("opportunity.read_again")}
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {editing ? (
        tailored ? <OpportunityForm opportunity={opportunity} onDone={() => setEditing(false)} />
          : schema ? <SchemaOpportunityForm opportunity={opportunity} schema={schema} onDone={() => setEditing(false)} /> : null
      ) : extraction.status !== "pending" ? (
        tailored || !schema ? <OpportunityDetails opportunity={opportunity} /> : <SchemaOpportunityDetails opportunity={opportunity} schema={schema} />
      ) : null}

      {extractAgain.error ? <ErrorNotice message={error(isApiError(extractAgain.error) ? extractAgain.error.code : "INTERNAL")} /> : null}
    </section>
  );
}

function OpportunityDetails({ opportunity }: { opportunity: Opportunity }) {
  const { t, date } = useI18n();
  const workplace = attr(opportunity, "workplace");
  const rows: [MessageKey, string][] = [
    ["opportunity.location", attr(opportunity, "location")],
    ["opportunity.workplace", workplace ? t(`opportunity.workplace.${workplace as "onsite" | "hybrid" | "remote"}`) : ""],
    ["opportunity.employment_type", attr(opportunity, "employment_type")],
    ["opportunity.salary_text", attr(opportunity, "salary_text")],
    ["opportunity.visa_sponsorship_text", attr(opportunity, "visa_sponsorship_text")],
    ["opportunity.hiring_manager", attr(opportunity, "hiring_manager")],
    ["opportunity.deadline", opportunity.deadline ? date(opportunity.deadline) : ""],
  ];
  const description = attr(opportunity, "description_markdown");
  return (
    <div className="space-y-4">
      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        {rows.filter(([, value]) => value).map(([label, value]) => (
          <div key={label}>
            <dt className="text-muted-foreground">{t(label)}</dt>
            <dd className="font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      <Description markdown={description} />
      <ReadBy opportunity={opportunity} />
    </div>
  );
}

function Description({ markdown }: { markdown: string }) {
  const { t } = useI18n();
  if (!markdown) return null;
  return (
    <details className="group rounded-lg border p-3">
      <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium">{t("opportunity.description_markdown")}</summary>
      <div className="prose-sm mt-2 max-w-none space-y-2 text-sm [&_li]:ms-5 [&_li]:list-disc">
        <SafeMarkdown>{markdown}</SafeMarkdown>
      </div>
    </details>
  );
}

function ReadBy({ opportunity }: { opportunity: Opportunity }) {
  const { t } = useI18n();
  const method = opportunity.extraction.method;
  const key: MessageKey = method === "source" ? forPack("opportunity.read_by.source", opportunity.pack) : `opportunity.read_by.${method}`;
  return (
    <p className="text-xs text-muted-foreground">
      {t(key)}
      {opportunity.extraction.edited ? ` · ${t("opportunity.edited")}` : ""}
    </p>
  );
}

// The page's header already shows the title; the description opens on its own.
const SHOWN_ELSEWHERE = ["title", "description_markdown"];

/** Any other pack's fields, drawn from its schema: only the filled ones. */
function SchemaOpportunityDetails({ opportunity, schema }: { opportunity: Opportunity; schema: JsonSchema }) {
  const { t, locale, date } = useI18n();
  const labels = useSchemaLabels();
  const attributes = opportunity.attributes as Value;
  return (
    <div className="space-y-4">
      <SchemaView schema={schema} value={attributes} locale={locale} item={labels.item} skip={SHOWN_ELSEWHERE} />
      {opportunity.deadline ? (
        <p className="text-sm"><span className="text-muted-foreground">{t("opportunity.deadline")}: </span>{date(opportunity.deadline)}</p>
      ) : null}
      <Description markdown={typeof attributes.description_markdown === "string" ? attributes.description_markdown : ""} />
      <ReadBy opportunity={opportunity} />
    </div>
  );
}

function SchemaOpportunityForm({ opportunity, schema, onDone }: { opportunity: Opportunity; schema: JsonSchema; onDone: () => void }) {
  const { t, error, locale } = useI18n();
  const labels = useSchemaLabels();
  const update = useUpdateOpportunity(opportunity.id);
  const fields = fieldsOf(schema);
  const [values, setValues] = useState<Value>(() => toFormValue(fields, opportunity.attributes as Value));
  const fieldErrors = isApiError(update.error) ? errorsUnder(update.error.fieldErrors, "attributes") : {};

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await update.mutateAsync({ attributes: cleanValue(fields, values) });
      toast(t("state.saved"));
      onDone();
    } catch {
      // Shown in the form.
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {update.error ? <ErrorNotice message={error(isApiError(update.error) ? update.error.code : "INTERNAL")} /> : null}
      <SchemaForm schema={schema} fields={fields} value={values} onChange={setValues} locale={locale} labels={labels} errors={fieldErrors} />
      <div className="flex gap-2">
        <Button type="submit" disabled={update.isPending}>{update.isPending ? t("action.saving") : t("action.save")}</Button>
        <Button type="button" variant="outline" onClick={onDone}>{t("action.cancel")}</Button>
      </div>
    </form>
  );
}

function OpportunityForm({ opportunity, onDone }: { opportunity: Opportunity; onDone: () => void }) {
  const { t, error } = useI18n();
  const update = useUpdateOpportunity(opportunity.id);
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(
    [...FIELDS, "workplace", "description_markdown"].map((key) => [key, attr(opportunity, key)])));
  const fieldErrors = isApiError(update.error) ? update.error.fieldErrors : {};

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await update.mutateAsync({ attributes: values });
      toast(t("state.saved"));
      onDone();
    } catch {
      // Shown in the form.
    }
  }

  const input = (key: Field) => {
    const message = fieldErrors[`attributes.${key}`];
    return (
      <div key={key} className="space-y-1">
        <Label htmlFor={`opp-${key}`}>{t(`opportunity.${key}`)}</Label>
        <Input id={`opp-${key}`} value={values[key] ?? ""} onChange={(e) => setValues((v) => ({ ...v, [key]: e.target.value }))}
          aria-invalid={message ? true : undefined} aria-describedby={message ? `opp-${key}-error` : undefined} />
        {message ? <p id={`opp-${key}-error`} className="text-sm text-destructive">{message}</p> : null}
      </div>
    );
  };

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {update.error ? <ErrorNotice message={error(isApiError(update.error) ? update.error.code : "INTERNAL")} /> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        {FIELDS.map(input)}
        <div className="space-y-1">
          <Label htmlFor="opp-workplace">{t("opportunity.workplace")}</Label>
          <select id="opp-workplace" value={values.workplace ?? ""} onChange={(e) => setValues((v) => ({ ...v, workplace: e.target.value }))}
            className="flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm">
            {WORKPLACES.map((w) => (
              <option key={w} value={w}>{w ? t(`opportunity.workplace.${w}`) : t("opportunity.workplace.unknown")}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="space-y-1">
        <Label htmlFor="opp-description">{t("opportunity.description_markdown")}</Label>
        <Textarea id="opp-description" rows={8} value={values.description_markdown ?? ""}
          onChange={(e) => setValues((v) => ({ ...v, description_markdown: e.target.value }))} />
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={update.isPending}>{update.isPending ? t("action.saving") : t("action.save")}</Button>
        <Button type="button" variant="outline" onClick={onDone}>{t("action.cancel")}</Button>
      </div>
    </form>
  );
}
