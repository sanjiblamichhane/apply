"use client";

import { useI18n } from "@apply/i18n/react";
import { PageHeader } from "@apply/kit";
import { useTheme } from "next-themes";
import { useId, useSyncExternalStore } from "react";

import { Help } from "@/components/help";
import { LanguageSwitch } from "@/components/language-switch";
import { ModelSection } from "@/components/model-settings";
import { PeopleSection } from "@/components/people-section";
import { AutoSection } from "@/components/auto-settings";
import { TemplatesSection } from "@/components/templates-section";
import { TokensSection } from "@/components/tokens-section";
import { useUpdateBriefingTime } from "@/lib/discovery";
import { useMe } from "@/lib/queries";

const THEMES = ["system", "light", "dark"] as const;
const mounted = () => true;

export default function SettingsPage() {
  const { t } = useI18n();
  const me = useMe();
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <title>{`${t("settings.title")} · apply`}</title>
      <PageHeader help={<Help slug="settings" />} title={t("settings.title")} />
      <section aria-labelledby="language-heading" className="space-y-2 rounded-xl border bg-card p-4">
        <h2 id="language-heading" className="text-lg font-semibold">{t("settings.language")}</h2>
        <p className="text-sm text-muted-foreground">{t("settings.language_hint")}</p>
        <LanguageSwitch signedIn />
      </section>
      <Appearance />
      <BriefingTime />
      <TemplatesSection />
      <ModelSection />
      <AutoSection />
      <TokensSection />
      <PeopleSection />
      <section aria-labelledby="account-heading" className="space-y-2 rounded-xl border bg-card p-4">
        <h2 id="account-heading" className="text-lg font-semibold">{t("settings.account")}</h2>
        {me.data ? <p className="text-sm">{t("settings.signed_in_as", { email: me.data.email })}</p> : null}
      </section>
    </div>
  );
}

function Appearance() {
  const { t } = useI18n();
  const { theme, setTheme } = useTheme();
  const name = useId();
  // The theme is only known in the browser; render the choice once it is.
  const ready = useSyncExternalStore(() => () => {}, mounted, () => false);
  return (
    <section aria-labelledby="appearance-heading" className="space-y-2 rounded-xl border bg-card p-4">
      <h2 id="appearance-heading" className="text-lg font-semibold">{t("settings.appearance")}</h2>
      <fieldset className="flex flex-wrap gap-2">
        <legend className="sr-only">{t("settings.appearance")}</legend>
        {THEMES.map((option) => (
          <label key={option} className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
            <input type="radio" name={name} value={option} checked={ready && theme === option} onChange={() => setTheme(option)} className="size-4 accent-[var(--primary)]" />
            {t(`settings.appearance.${option}`)}
          </label>
        ))}
      </fieldset>
    </section>
  );
}

function BriefingTime() {
  const { t } = useI18n();
  const me = useMe();
  const update = useUpdateBriefingTime();
  if (!me.data) return null;
  const zones = Intl.supportedValuesOf?.("timeZone") ?? ["UTC"];
  return (
    <section aria-labelledby="briefing-heading" className="space-y-3 rounded-xl border bg-card p-4">
      <h2 id="briefing-heading" className="text-lg font-semibold">{t("settings.briefing")}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="briefing-hour" className="text-sm font-medium">{t("settings.briefing_hour")}</label>
          <select id="briefing-hour" value={me.data.briefing_hour} onChange={(e) => update.mutate({ briefing_hour: Number(e.target.value) })}
            className="flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm">
            {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="time-zone" className="text-sm font-medium">{t("settings.time_zone")}</label>
          <select id="time-zone" value={me.data.time_zone} onChange={(e) => update.mutate({ time_zone: e.target.value })}
            className="flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm">
            {(zones.includes(me.data.time_zone) ? zones : [me.data.time_zone, ...zones]).map((z) => <option key={z} value={z}>{z}</option>)}
          </select>
        </div>
      </div>
    </section>
  );
}

