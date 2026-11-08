"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import { Time } from "@apply/ui/icons";

import { Help } from "@/components/help";
import { AutoRunCard } from "@/components/auto-run";
import { PausedBanner, PauseAutoSwitch } from "@/components/pause-auto";
import { useRuns } from "@/lib/auto";

/** Ready for you: what Auto prepared, for the person to send; then what's still being prepared, and what was sent. */
export default function ReadyPage() {
  const { t, error } = useI18n();
  const ready = useRuns("ready");
  const preparing = useRuns("waiting");
  const done = useRuns("done");
  const sent = (done.data ?? []).filter((r) => r.status === "sent").slice(0, 10);
  const failure = ready.error ?? preparing.error;
  const nothing = ready.isSuccess && preparing.isSuccess && ready.data.length === 0 && preparing.data.length === 0;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${t("shell.ready")} · apply`}</title>
      <PageHeader help={<Help slug="auto" />} title={t("shell.ready")} description={t("auto.ready.description")} actions={<PauseAutoSwitch />} />
      <PausedBanner />
      {failure ? <ErrorNotice message={error(isApiError(failure) ? failure.code : "INTERNAL")} /> : null}
      {nothing ? <EmptyState icon={Time} title={t("auto.ready.empty")} body={t("auto.ready.empty_body")} /> : null}
      <ul className="space-y-3">{(ready.data ?? []).map((run) => <AutoRunCard key={run.id} run={run} />)}</ul>
      {preparing.data?.length ? (
        <section aria-labelledby="preparing-heading" className="space-y-3">
          <h2 id="preparing-heading" className="text-lg font-semibold">{t("auto.preparing")}</h2>
          <ul className="space-y-3">{preparing.data.map((run) => <AutoRunCard key={run.id} run={run} />)}</ul>
        </section>
      ) : null}
      {sent.length ? (
        <section aria-labelledby="sent-heading" className="space-y-3">
          <h2 id="sent-heading" className="text-lg font-semibold">{t("auto.sent_recently")}</h2>
          <ul className="space-y-3">{sent.map((run) => <AutoRunCard key={run.id} run={run} />)}</ul>
        </section>
      ) : null}
    </div>
  );
}
