"use client";

import { isApiError, type NewSearch, type Search } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label, Textarea } from "@apply/ui";
import { type FormEvent, type ReactNode, useId, useState } from "react";

import { lines, searchOptionsFor, useSources } from "@/lib/discovery";
import { useCurrentPack } from "@/lib/pack-choice";
import { usePack, useProfiles } from "@/lib/queries";

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: (describedBy?: string) => ReactNode }) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      {hint ? <p id={`${id}-hint`} className="text-sm text-muted-foreground">{hint}</p> : null}
      {children(hint ? `${id}-hint` : undefined)}
    </div>
  );
}

function Check({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  const id = useId();
  return (
    <div>
      <label className="flex min-h-11 items-center gap-3 text-sm">
        <input type="checkbox" className="size-5 accent-[var(--primary)]" checked={checked} onChange={(e) => onChange(e.target.checked)}
          aria-describedby={hint ? `${id}-hint` : undefined} />
        {label}
      </label>
      {hint ? <p id={`${id}-hint`} className="ps-8 text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** A search's rules, as a form. Lists are one item per line, as in the profile form. */
export function SearchForm({ search, saving, error, onSubmit }: {
  search?: Search; saving: boolean; error: unknown; onSubmit: (body: NewSearch) => void;
}) {
  const { t, error: errorText } = useI18n();
  const [chosenPack] = useCurrentPack();
  const currentPack = search?.pack ?? chosenPack; // a search stays in its own pack
  const shown = searchOptionsFor(usePack(currentPack).data);
  const base = useId();
  const sources = useSources(currentPack);
  const profiles = useProfiles(currentPack);
  const c = search?.criteria;
  const [name, setName] = useState(search?.name ?? "");
  const [keywords, setKeywords] = useState((c?.keywords ?? []).join("\n"));
  const [matchAll, setMatchAll] = useState(c?.match_all ?? false);
  const [exclude, setExclude] = useState((c?.exclude ?? []).join("\n"));
  const [locations, setLocations] = useState((c?.locations ?? []).join("\n"));
  const [remoteOnly, setRemoteOnly] = useState(c?.remote_only ?? false);
  const [needsSponsorship, setNeedsSponsorship] = useState(c?.needs_sponsorship ?? false);
  const [sourceIds, setSourceIds] = useState<string[]>(c?.source_ids ?? []);
  const [profileId, setProfileId] = useState(search?.profile_id ?? "");
  const [enabled, setEnabled] = useState(search?.enabled ?? true);
  const [auto, setAuto] = useState(search?.auto_enabled ?? false);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      pack: currentPack, name: name.trim(), enabled, auto_enabled: shown.auto && auto, profile_id: profileId || null, min_score: search?.min_score ?? 0,
      criteria: { keywords: lines(keywords), match_all: matchAll, exclude: lines(exclude), locations: lines(locations),
                  remote_only: shown.remoteOnly && remoteOnly, needs_sponsorship: shown.needsSponsorship && needsSponsorship,
                  source_ids: sourceIds },
    });
  }

  return (
    <form onSubmit={submit} className="space-y-6" noValidate>
      {error ? <ErrorNotice message={errorText(isApiError(error) ? error.code : "INTERNAL")} /> : null}
      <fieldset className="space-y-4 rounded-xl border bg-card p-4">
        <legend className="px-1 text-lg font-semibold">{t("searches.name")}</legend>
        <Field id={`${base}-name`} label={t("searches.name")}>
          {(d) => <Input id={`${base}-name`} value={name} onChange={(e) => setName(e.target.value)} aria-describedby={d} />}
        </Field>
        <Check checked={enabled} onChange={setEnabled} label={t("searches.enabled")} />
        {shown.auto ? <Check checked={auto} onChange={setAuto} label={t("searches.auto")} hint={t("searches.auto_hint")} /> : null}
      </fieldset>
      <fieldset className="space-y-4 rounded-xl border bg-card p-4">
        <legend className="px-1 text-lg font-semibold">{t("searches.keywords")}</legend>
        <Field id={`${base}-keywords`} label={t("searches.keywords")} hint={t("searches.keywords_hint")}>
          {(d) => <Textarea id={`${base}-keywords`} rows={4} value={keywords} onChange={(e) => setKeywords(e.target.value)} aria-describedby={d} />}
        </Field>
        <Check checked={matchAll} onChange={setMatchAll} label={t("searches.match_all")} />
        <Field id={`${base}-exclude`} label={t(forPack("searches.exclude", currentPack))} hint={t("searches.exclude_hint")}>
          {(d) => <Textarea id={`${base}-exclude`} rows={3} value={exclude} onChange={(e) => setExclude(e.target.value)} aria-describedby={d} />}
        </Field>
      </fieldset>
      {shown.locations || shown.remoteOnly || shown.needsSponsorship ? (
        <fieldset className="space-y-4 rounded-xl border bg-card p-4">
          <legend className="px-1 text-lg font-semibold">{t("searches.locations")}</legend>
          {shown.locations ? (
            <Field id={`${base}-locations`} label={t("searches.locations")} hint={t(forPack("searches.locations_hint", currentPack))}>
              {(d) => <Textarea id={`${base}-locations`} rows={3} value={locations} onChange={(e) => setLocations(e.target.value)} aria-describedby={d} />}
            </Field>
          ) : null}
          {shown.remoteOnly ? <Check checked={remoteOnly} onChange={setRemoteOnly} label={t("searches.remote_only")} /> : null}
          {shown.needsSponsorship ? (
            <Check checked={needsSponsorship} onChange={setNeedsSponsorship} label={t("searches.needs_sponsorship")} hint={t("searches.needs_sponsorship_hint")} />
          ) : null}
        </fieldset>
      ) : null}
      <fieldset className="space-y-3 rounded-xl border bg-card p-4">
        <legend className="px-1 text-lg font-semibold">{t("searches.sources")}</legend>
        <p className="text-sm text-muted-foreground">{t("searches.sources_hint")}</p>
        {(sources.data ?? []).map((source) => (
          <Check key={source.id} checked={sourceIds.includes(source.id)} label={source.name}
            onChange={(on) => setSourceIds((ids) => (on ? [...ids, source.id] : ids.filter((x) => x !== source.id)))} />
        ))}
      </fieldset>
      <fieldset className="space-y-3 rounded-xl border bg-card p-4">
        <legend className="px-1 text-lg font-semibold">{t("searches.profile")}</legend>
        <Field id={`${base}-profile`} label={t("searches.profile")}>
          {() => (
            <select id={`${base}-profile`} value={profileId} onChange={(e) => setProfileId(e.target.value)}
              className="flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm">
              <option value="">{t("searches.profile_default")}</option>
              {(profiles.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          )}
        </Field>
      </fieldset>
      <Button type="submit" disabled={saving || !name.trim()}>{saving ? t("action.saving") : t("action.save")}</Button>
    </form>
  );
}
