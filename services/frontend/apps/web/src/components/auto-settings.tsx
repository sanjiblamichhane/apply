"use client";

/** Settings → Auto: Pause Auto, and the limits on what it prepares. It never sends: the person does. */
import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label } from "@apply/ui";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import { PauseAutoSwitch } from "@/components/pause-auto";
import { useAutoSettings, useUpdateAutoSettings } from "@/lib/auto";

export function AutoSection() {
  const { t } = useI18n();
  const settings = useAutoSettings();
  return (
    <section aria-labelledby="auto-heading" className="space-y-4 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-1"><h2 id="auto-heading" className="text-lg font-semibold">{t("settings.auto")}</h2><Help slug="auto" /></div>
      <p className="text-sm text-muted-foreground">{t("settings.auto_hint")}</p>
      <PauseAutoSwitch />
      {settings.data ? <Limits key={settings.dataUpdatedAt} initial={settings.data} /> : null}
    </section>
  );
}

function Limits({ initial }: { initial: { auto_min_score: number; auto_daily_cap: number } }) {
  const { t, error } = useI18n();
  const update = useUpdateAutoSettings();
  const [minScore, setMinScore] = useState(String(initial.auto_min_score));
  const [cap, setCap] = useState(String(initial.auto_daily_cap));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    update.mutate(
      { auto_min_score: Number(minScore), auto_daily_cap: Number(cap) },
      { onSuccess: () => toast(t("settings.auto_saved")) },
    );
  };
  const number = (id: string, label: string, value: string, set: (v: string) => void, min: number, max: number) => (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type="number" inputMode="numeric" min={min} max={max} step={1} value={value} required
        onChange={(e) => set(e.target.value)} className="max-w-32" />
    </div>
  );
  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {number("auto-min-score", t("settings.auto_min_score"), minScore, setMinScore, 0, 100)}
        {number("auto-cap", t("settings.auto_daily_cap"), cap, setCap, 0, 50)}
      </div>
      {update.error ? <ErrorNotice message={error(isApiError(update.error) ? update.error.code : "INTERNAL")} /> : null}
      <Button type="submit" disabled={update.isPending}>{t("action.save")}</Button>
    </form>
  );
}
