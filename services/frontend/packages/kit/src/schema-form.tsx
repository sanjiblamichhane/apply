"use client";

/**
 * A form and a view drawn from a pack's JSON schema, so a new pack needs no screen code. Each field's label comes
 * from its `x-label` ({en, ne}); `x-options` labels an enum's values; `x-long` asks for a text area. What it draws:
 * strings, enums, long text, lists of strings (one per line), and lists of objects (each item a group of its own
 * fields, with Add and Remove).
 */
import { Button, Input, Label, Textarea } from "@apply/ui";
import { Add, Trash } from "@apply/ui/icons";
import { type ReactNode, useId } from "react";

/** A language code ("en", "ne", "es"): labels fall back to English where one has no text in it. */
export type Locale = string;
export type Value = Record<string, unknown>;
type Bilingual = Partial<Record<Locale, string>>;

export interface JsonSchema {
  type?: string;
  enum?: string[];
  items?: JsonSchema;
  properties?: Record<string, JsonSchema>;
  $ref?: string;
  $defs?: Record<string, JsonSchema>;
  maxLength?: number;
  "x-label"?: Bilingual;
  "x-options"?: Record<string, Bilingual>;
  "x-long"?: boolean;
}

export type FieldKind = "text" | "long" | "choice" | "list" | "group";

export interface SchemaField {
  key: string;
  kind: FieldKind;
  label: Bilingual;
  options: { value: string; label: Bilingual }[];
  /** For a list of groups: the item's own fields. */
  fields: SchemaField[];
  maxLength?: number;
}

const LONG = 1000; // a string this long or longer gets a text area

function resolve(root: JsonSchema, node: JsonSchema | undefined): JsonSchema {
  if (!node?.$ref) return node ?? {};
  const name = node.$ref.split("/").pop() ?? "";
  return root.$defs?.[name] ?? {};
}

/** The fields a schema node (the root, or a list item's object) has, in the schema's order. */
export function fieldsOf(root: JsonSchema, node: JsonSchema = root): SchemaField[] {
  return Object.entries(resolve(root, node).properties ?? {}).map(([key, raw]) => {
    const prop = resolve(root, raw);
    const label = prop["x-label"] ?? { en: key, ne: key };
    const base = { key, label, options: [], fields: [], maxLength: prop.maxLength };
    if (prop.enum) {
      const names = prop["x-options"] ?? {};
      return { ...base, kind: "choice", options: prop.enum.map((v) => ({ value: v, label: names[v] ?? { en: v, ne: v } })) };
    }
    if (prop.type === "array") {
      const item = resolve(root, prop.items);
      if (item.properties) return { ...base, kind: "group", fields: fieldsOf(root, item) };
      return { ...base, kind: "list" };
    }
    const long = prop["x-long"] || (prop.maxLength ?? 0) >= LONG;
    return { ...base, kind: long ? "long" : "text" };
  });
}

/** An empty value for these fields: "" for text, [] for lists. */
export function emptyOf(fields: SchemaField[]): Value {
  return Object.fromEntries(fields.map((f) => [f.key, f.kind === "list" || f.kind === "group" ? [] : ""]));
}

/** What's stored, as the form edits it: every field present (missing ones empty), nothing the schema lacks. */
export function toFormValue(fields: SchemaField[], value: Value | null | undefined): Value {
  const out = emptyOf(fields);
  for (const f of fields) {
    const v = value?.[f.key];
    if (f.kind === "group") out[f.key] = Array.isArray(v) ? v.map((item) => toFormValue(f.fields, item as Value)) : [];
    else if (f.kind === "list") out[f.key] = Array.isArray(v) ? v.map(String) : [];
    else out[f.key] = v == null ? "" : String(v);
  }
  return out;
}

const blank = (v: unknown) => v == null || (typeof v === "string" && v.trim() === "") || (Array.isArray(v) && v.length === 0);

/** Ready to save: text trimmed, empty lines and wholly empty items dropped. */
export function cleanValue(fields: SchemaField[], value: Value): Value {
  const out: Value = {};
  for (const f of fields) {
    const v = value[f.key];
    if (f.kind === "group") {
      out[f.key] = (Array.isArray(v) ? v : [])
        .map((item) => cleanValue(f.fields, item as Value))
        .filter((item) => !Object.values(item).every(blank));
    } else if (f.kind === "list") {
      out[f.key] = (Array.isArray(v) ? v : []).map((s) => String(s).trim()).filter(Boolean);
    } else {
      out[f.key] = typeof v === "string" ? v.trim() : v ?? "";
    }
  }
  return out;
}

/** Whether a value has anything worth showing for these fields. */
export function isFilled(field: SchemaField, value: unknown): boolean {
  if (field.kind === "group") {
    return Array.isArray(value) && value.some((item) => field.fields.some((f) => isFilled(f, (item as Value)?.[f.key])));
  }
  return !blank(value) && !(Array.isArray(value) && value.every(blank));
}

export interface SchemaFormLabels {
  add: (itemLabel: string) => string;
  remove: (itemLabel: string, n: number) => string;
  item: (itemLabel: string, n: number) => string;
  onePerLine: string;
}

const control = "flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm";

/** The schema's fields as form controls. Controlled: ``value`` in, ``onChange`` with the whole new value. */
export function SchemaForm({ schema, fields, value, onChange, locale, labels, errors = {}, path = "" }: {
  schema: JsonSchema;
  fields?: SchemaField[];
  value: Value;
  onChange: (value: Value) => void;
  locale: Locale;
  labels: SchemaFormLabels;
  /** Errors by field path ("past_performance.0.year"), as the API's problem gives them. */
  errors?: Record<string, string>;
  path?: string;
}) {
  const base = useId();
  const list = fields ?? fieldsOf(schema);
  const name = (b: Bilingual) => b[locale] ?? b.en ?? "";
  const set = (key: string, v: unknown) => onChange({ ...value, [key]: v });

  return (
    <div className="space-y-4">
      {list.map((f) => {
        const id = `${base}-${f.key}`;
        const at = path ? `${path}.${f.key}` : f.key;
        const error = errors[at];
        if (f.kind === "group") {
          const items = (value[f.key] as Value[] | undefined) ?? [];
          return (
            <fieldset key={f.key} className="space-y-3">
              <legend className="text-sm font-semibold">{name(f.label)}</legend>
              {items.map((item, i) => (
                <fieldset key={i} className="space-y-3 rounded-lg border p-3">
                  <legend className="px-1 text-sm font-medium">{labels.item(name(f.label), i + 1)}</legend>
                  <SchemaForm schema={schema} fields={f.fields} value={item} locale={locale} labels={labels}
                    errors={errors} path={`${at}.${i}`}
                    onChange={(next) => set(f.key, items.map((it, j) => (j === i ? next : it)))} />
                  <Button type="button" variant="ghost" size="sm" className="gap-2"
                    onClick={() => set(f.key, items.filter((_, j) => j !== i))}>
                    <Trash aria-hidden />{labels.remove(name(f.label), i + 1)}
                  </Button>
                </fieldset>
              ))}
              <Button type="button" variant="outline" size="sm" className="gap-2"
                onClick={() => set(f.key, [...items, emptyOf(f.fields)])}>
                <Add aria-hidden />{labels.add(name(f.label))}
              </Button>
            </fieldset>
          );
        }
        return (
          <Field key={f.key} id={id} label={name(f.label)} hint={f.kind === "list" ? labels.onePerLine : undefined} error={error}>
            {(props) => {
              if (f.kind === "choice") {
                return (
                  <select {...props} className={control} value={String(value[f.key] ?? "")} onChange={(e) => set(f.key, e.target.value)}>
                    {f.options.map((o) => <option key={o.value} value={o.value}>{name(o.label)}</option>)}
                  </select>
                );
              }
              if (f.kind === "list") {
                const lines = ((value[f.key] as string[] | undefined) ?? []).join("\n");
                return <Textarea {...props} rows={4} value={lines} onChange={(e) => set(f.key, e.target.value.split("\n"))} />;
              }
              if (f.kind === "long") {
                return <Textarea {...props} rows={4} maxLength={f.maxLength} value={String(value[f.key] ?? "")}
                  onChange={(e) => set(f.key, e.target.value)} />;
              }
              return <Input {...props} maxLength={f.maxLength} value={String(value[f.key] ?? "")}
                onChange={(e) => set(f.key, e.target.value)} />;
            }}
          </Field>
        );
      })}
    </div>
  );
}

function Field({ id, label, hint, error, children }: {
  id: string; label: string; hint?: string; error?: string;
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

/** The filled fields only, as a description list; lists as lists, groups as their own small lists. */
export function SchemaView({ schema, fields, value, locale, item, skip = [] }: {
  schema: JsonSchema;
  fields?: SchemaField[];
  value: Value | null | undefined;
  locale: Locale;
  item: (itemLabel: string, n: number) => string;
  /** Fields the screen already shows elsewhere (the title, say). */
  skip?: string[];
}) {
  const list = (fields ?? fieldsOf(schema)).filter((f) => !skip.includes(f.key) && isFilled(f, value?.[f.key]));
  const name = (b: Bilingual) => b[locale] ?? b.en ?? "";
  if (list.length === 0) return null;
  return (
    <dl className="grid gap-x-4 gap-y-3 sm:grid-cols-[minmax(8rem,auto)_1fr]">
      {list.map((f) => {
        const v = value?.[f.key];
        let shown: ReactNode;
        if (f.kind === "group") {
          shown = (
            <ol className="space-y-3">
              {(v as Value[]).map((entry, i) => isFilled(f, [entry]) ? (
                <li key={i} className="rounded-lg border p-3">
                  <p className="sr-only">{item(name(f.label), i + 1)}</p>
                  <SchemaView schema={schema} fields={f.fields} value={entry} locale={locale} item={item} />
                </li>
              ) : null)}
            </ol>
          );
        } else if (f.kind === "list") {
          shown = <ul className="list-disc space-y-1 ps-5">{(v as string[]).filter((s) => !blank(s)).map((s, i) => <li key={i}>{s}</li>)}</ul>;
        } else if (f.kind === "choice") {
          shown = name(f.options.find((o) => o.value === v)?.label ?? { en: String(v) });
        } else {
          shown = <span className="whitespace-pre-line">{String(v)}</span>;
        }
        return (
          <div key={f.key} className="contents">
            <dt className="text-sm font-medium text-muted-foreground">{name(f.label)}</dt>
            <dd className="min-w-0 break-words text-sm">{shown}</dd>
          </div>
        );
      })}
    </dl>
  );
}
