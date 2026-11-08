"use client";

import { isApiError } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice, PageHeader } from "@apply/kit";
import { Button, Input, Label } from "@apply/ui";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { useCurrentPack } from "@/lib/pack-choice";
import { useCreateSource, useRecogniseSource, useSourceKinds } from "@/lib/discovery";

export default function NewSourcePage() {
  const { t, error, pick } = useI18n();
  const [currentPack] = useCurrentPack();
  const router = useRouter();
  const kinds = useSourceKinds();
  const create = useCreateSource();
  const recognise = useRecogniseSource();
  // A company's job board is recognised from its address; other kinds (a public tender feed) are chosen from a list.
  const listed = (kinds.data ?? []).filter((k) => !k.from_address);
  const byAddress = (kinds.data ?? []).some((k) => k.from_address);
  const [address, setAddress] = useState("");
  const [recognised, setRecognised] = useState<string | null>(null);
  const [chosen, setKindKey] = useState<string | null>(null);
  // What the address stands for, else the chosen kind, else the list's first (and again if the pack changes).
  const kindKey = recognised ?? (listed.some((k) => k.kind === chosen) ? chosen! : listed[0]?.kind ?? "");
  const [config, setConfig] = useState<Record<string, string>>({});
  const [name, setName] = useState("");
  const [interval, setInterval] = useState("6");
  const kind = kinds.data?.find((k) => k.kind === kindKey);
  const fieldErrors = isApiError(create.error) ? create.error.fieldErrors : {};

  // Recognised a moment after the person stops typing (or pastes); the kind's fields are then filled in.
  const { mutate: recogniseAddress, reset: resetRecognise } = recognise;
  useEffect(() => {
    const url = address.trim();
    if (!/^https?:\/\/\S+\.\S+/i.test(url)) return;
    const timer = setTimeout(() => recogniseAddress(url, {
      onSuccess: (found) => { setRecognised(found.kind); setConfig(found.config); },
    }), 400);
    return () => clearTimeout(timer);
  }, [address, recogniseAddress]);
  const changeAddress = (value: string) => { setAddress(value); setRecognised(null); setConfig({}); resetRecognise(); };

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ pack: currentPack, kind: kindKey, config, name: name.trim() || null, interval_hours: Number(interval) || 6, enabled: true }, {
      onSuccess: () => {
        toast(t("sources.saved"));
        router.push("/sources");
      },
    });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <title>{`${t("sources.new")} · apply`}</title>
      <PageHeader help={<Help slug="sources" />} title={t("sources.new")} description={t(forPack("sources.description", currentPack))} />
      <form onSubmit={submit} className="space-y-6 rounded-xl border bg-card p-4" noValidate>
        {create.error ? <ErrorNotice message={error(isApiError(create.error) ? create.error.code : "INTERNAL")} /> : null}
        {byAddress ? (
          <div className="space-y-1">
            <Label htmlFor="source-address">{t("sources.address")}</Label>
            <p id="source-address-hint" className="text-sm text-muted-foreground">{t("sources.address_hint")}</p>
            <Input id="source-address" type="url" inputMode="url" autoComplete="off" value={address}
              onChange={(e) => changeAddress(e.target.value)} aria-invalid={recognise.isError ? true : undefined}
              aria-describedby={`source-address-hint source-address-status`} />
            <p id="source-address-status" role="status" aria-live="polite"
              className={`text-sm ${recognise.isError ? "text-destructive" : "text-muted-foreground"}`}>
              {recognise.isPending ? t("sources.recognising")
                : recognise.isError ? error(isApiError(recognise.error) ? recognise.error.code : "INTERNAL")
                : recognised ? t("sources.recognised") : null}
            </p>
          </div>
        ) : null}
        {listed.length > 0 ? (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">{t("sources.kind")}</legend>
          {listed.map((k) => (
            <label key={k.kind} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-md border border-input p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
              <input type="radio" name="kind" value={k.kind} checked={kindKey === k.kind} className="mt-1 size-4 accent-[var(--primary)]"
                onChange={() => { setKindKey(k.kind); setConfig({}); setInterval(String(Math.max(6, k.min_interval_hours))); }} />
              <span>
                <span className="block font-medium">{pick(k.label)}</span>
                <span className="block text-sm text-muted-foreground">{pick(k.description)}</span>
              </span>
            </label>
          ))}
        </fieldset>
        ) : null}
        {kind?.fields.map((field) => {
          const id = `source-${field.key}`;
          const message = fieldErrors[`config.${field.key}`];
          return (
            <div key={field.key} className="space-y-1">
              <Label htmlFor={id}>{pick(field.label)}{field.required ? null : <span className="font-normal text-muted-foreground"> ({t("state.optional")})</span>}</Label>
              <p id={`${id}-hint`} className="text-sm text-muted-foreground">{pick(field.hint)}</p>
              <Input id={id} value={config[field.key] ?? ""} required={field.required} aria-invalid={message ? true : undefined}
                aria-describedby={`${id}-hint${message ? ` ${id}-error` : ""}`}
                onChange={(e) => setConfig((c) => ({ ...c, [field.key]: e.target.value }))} />
              {message ? <p id={`${id}-error`} className="text-sm text-destructive">{message}</p> : null}
            </div>
          );
        })}
        <div className="space-y-1">
          <Label htmlFor="source-name">{t("sources.name")} <span className="font-normal text-muted-foreground">({t("state.optional")})</span></Label>
          <p id="source-name-hint" className="text-sm text-muted-foreground">{t(forPack("sources.name_hint", currentPack))}</p>
          <Input id="source-name" value={name} onChange={(e) => setName(e.target.value)} aria-describedby="source-name-hint" />
        </div>
        <div className="space-y-1">
          <Label htmlFor="source-interval">{t("sources.interval")}</Label>
          <p id="source-interval-hint" className="text-sm text-muted-foreground">{t(forPack("sources.interval_hint", currentPack), { hours: kind?.min_interval_hours ?? 1 })}</p>
          <Input id="source-interval" type="number" inputMode="numeric" min={kind?.min_interval_hours ?? 1} max={168} value={interval}
            onChange={(e) => setInterval(e.target.value)} aria-describedby="source-interval-hint" className="max-w-32" />
        </div>
        {kind ? <p className="text-sm text-muted-foreground">{t("sources.terms")}: {pick(kind.terms)}</p> : null}
        <Button type="submit" disabled={create.isPending || !kind || kind.fields.some((f) => f.required && !config[f.key]?.trim())}>
          {create.isPending ? t("action.saving") : t("sources.new")}
        </Button>
      </form>
    </div>
  );
}
