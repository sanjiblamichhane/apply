"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import { CheckmarkFilled } from "@apply/ui/icons";

import { Help } from "@/components/help";
import { AutoRunCard } from "@/components/auto-run";
import { PausedBanner, PauseAutoSwitch } from "@/components/pause-auto";
import { useRuns } from "@/lib/auto";

export default function NeedsYouPage() {
  const { t, error } = useI18n();
  const runs = useRuns("needs_you");
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${t("shell.needs_you")} · apply`}</title>
      <PageHeader help={<Help slug="auto" />} title={t("shell.needs_you")} description={t("auto.needs_you.description")} actions={<PauseAutoSwitch />} />
      <PausedBanner />
      {runs.error ? <ErrorNotice message={error(isApiError(runs.error) ? runs.error.code : "INTERNAL")} /> : null}
      {runs.isSuccess && runs.data.length === 0 ? <EmptyState icon={CheckmarkFilled} title={t("auto.needs_you.empty")} /> : null}
      <ul className="space-y-3">{(runs.data ?? []).map((run) => <AutoRunCard key={run.id} run={run} />)}</ul>
    </div>
  );
}
