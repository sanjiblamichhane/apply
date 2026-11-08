"use client";

import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import { Button } from "@apply/ui";
import { Search, Sun, Time, WarningAlt } from "@apply/ui/icons";
import Link from "next/link";

import { Help } from "@/components/help";
import { useAutoCounts } from "@/lib/auto";
import { useBriefing, useBuildBriefing } from "@/lib/discovery";
import { DEFAULT_PACK } from "@/lib/pack-choice";
import { useMe, usePacks } from "@/lib/queries";

export default function TodayPage() {
  const { t, error, pick, date, locale } = useI18n();
  const briefing = useBriefing();
  const build = useBuildBriefing();
  const me = useMe();
  const packs = usePacks().data;
  const content = briefing.data?.content;
  const auto = useAutoCounts().data;
  const packOf = (key: string | undefined) => packs?.find((p) => p.key === (key ?? DEFAULT_PACK));
  const stage = (key: string | undefined, code: string) => pick(packOf(key)?.pipeline.stages.find((s) => s.code === code)?.label) || code;
  // Today covers every pack: when it holds more than one, each line says which.
  const inToday = new Set([...(content?.new_matches.top ?? []), ...(content?.follow_ups ?? []), ...(content?.deadlines ?? [])].map((x) => x.pack ?? DEFAULT_PACK));
  const from = (key: string | undefined, issuer: string) => (inToday.size > 1 ? `${pick(packOf(key)?.label) || key} · ${issuer}` : issuer);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <title>{`${t("today.title")} · apply`}</title>
      <PageHeader help={<Help slug="today" />} title={t("today.title")} description={t("today.description")}
        actions={briefing.data ? <span className="text-sm text-muted-foreground">{date(briefing.data.date + "T12:00:00", { weekday: "long", day: "numeric", month: "long" } as Intl.DateTimeFormatOptions)}</span> : null} />
      {briefing.error ? <ErrorNotice message={error((briefing.error as { code?: string }).code)} retryLabel={t("action.retry")} onRetry={() => briefing.refetch()} /> : null}

      {briefing.isSuccess && !briefing.data ? (
        <EmptyState icon={Sun} title={t("today.not_built", { hour: me.data?.briefing_hour ?? 7 })}
          body={t("today.get_started")}
          action={<Button onClick={() => build.mutate()} disabled={build.isPending}>{t("today.build")}</Button>} />
      ) : null}

      {auto && (auto.ready > 0 || auto.waiting > 0 || auto.needs_you > 0) ? (
        <section aria-labelledby="auto-heading" className="space-y-3 rounded-xl border bg-card p-4">
          <h2 id="auto-heading" className="text-lg font-semibold">{t("today.auto")}</h2>
          <p className="text-sm">{t("today.auto_line", { ready: auto.ready, waiting: auto.waiting, needs_you: auto.needs_you })}</p>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" className="gap-2"><Link href="/ready"><Time aria-hidden />{t("shell.ready")}</Link></Button>
            <Button asChild variant="outline" className="gap-2"><Link href="/needs-you"><WarningAlt aria-hidden />{t("shell.needs_you")}</Link></Button>
          </div>
        </section>
      ) : null}

      {content ? (
        <>
          <section aria-labelledby="new-heading" className="space-y-3 rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="new-heading" className="text-lg font-semibold">{t("today.new_matches")}</h2>
              <p className="text-sm text-muted-foreground">{t("today.new_matches_count", { count: content.new_matches.count })}</p>
            </div>
            {content.new_matches.top.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("today.none_new")}</p>
            ) : (
              <ol className="divide-y">
                {content.new_matches.top.map((m) => (
                  <li key={m.match_id} className="flex items-center justify-between gap-3 py-2">
                    <div className="min-w-0">
                      <p className="font-medium">{m.title}</p>
                      <p className="truncate text-sm text-muted-foreground">{from(m.pack, m.issuer_name)}</p>
                    </div>
                    {m.score !== null ? <span className="shrink-0 text-sm font-semibold tabular-nums">{t("matches.fit", { score: m.score })}</span> : null}
                  </li>
                ))}
              </ol>
            )}
            <Button asChild variant="outline" className="gap-2"><Link href="/matches"><Search aria-hidden />{t("today.see_all")}</Link></Button>
          </section>

          <section aria-labelledby="followups-heading" className="space-y-3 rounded-xl border bg-card p-4">
            <h2 id="followups-heading" className="text-lg font-semibold">{t("today.follow_ups")}</h2>
            {content.follow_ups.length === 0 ? <p className="text-sm text-muted-foreground">{t("today.no_follow_ups")}</p> : (
              <ul className="divide-y">
                {content.follow_ups.map((f) => (
                  <li key={f.application_id} className="flex items-center gap-3 py-2">
                    <Time className="size-5 shrink-0 text-muted-foreground" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <Link href={`/applications/${f.application_id}`} className="font-medium text-primary underline-offset-4 hover:underline">{f.title}</Link>
                      <p className="text-sm text-muted-foreground">{from(f.pack, f.issuer_name)} · {t("today.follow_up_line", { days: f.days, stage: stage(f.pack, f.stage_code) })}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="deadlines-heading" className="space-y-3 rounded-xl border bg-card p-4">
            <h2 id="deadlines-heading" className="text-lg font-semibold">{t("today.deadlines")}</h2>
            {content.deadlines.length === 0 ? <p className="text-sm text-muted-foreground">{t("today.no_deadlines")}</p> : (
              <ul className="divide-y">
                {content.deadlines.map((d) => (
                  <li key={d.application_id} className="flex items-center gap-3 py-2">
                    <WarningAlt className="size-5 shrink-0 text-destructive" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <Link href={`/applications/${d.application_id}`} className="font-medium text-primary underline-offset-4 hover:underline">{d.title}</Link>
                      <p className="text-sm text-muted-foreground">{from(d.pack, d.issuer_name)} · <time dateTime={d.deadline}>{date(d.deadline)}</time></p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <Button variant="ghost" onClick={() => build.mutate()} disabled={build.isPending} lang={locale}>{t("today.build")}</Button>
        </>
      ) : null}
      {briefing.isLoading ? <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p> : null}
    </div>
  );
}
