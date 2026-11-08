"use client";

import type { Application } from "@apply/api";
import { formatNumber } from "@apply/i18n";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, KanbanBoard, PageHeader, SearchField, ViewSwitcher } from "@apply/kit";
import { Button } from "@apply/ui";
import { Board, DocumentAdd, List, User } from "@apply/ui/icons";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { useCurrentPack } from "@/lib/pack-choice";
import { boardStages, filterApplications, readListState, type View, writeListState } from "@/lib/board";
import { useApplications, useMove, usePack, useProfiles } from "@/lib/queries";

import { ApplicationCard } from "./application-card";
import { ApplicationsList } from "./applications-list";
import { PasteBox } from "./paste-box";

export function ApplicationsIndex({ beside = false }: { beside?: boolean }) {
  const { t, pick, locale, error } = useI18n();
  const [currentPack] = useCurrentPack();
  const pathname = usePathname();
  const params = useSearchParams();
  const { view, query } = readListState(params);
  const pack = usePack(currentPack);
  const applications = useApplications();
  const profiles = useProfiles();
  const move = useMove();

  const stages = useMemo(() => boardStages(pack.data?.pipeline.stages ?? []), [pack.data]);
  const shown = useMemo(() => filterApplications(applications.data ?? [], query), [applications.data, query]);
  const items = useMemo(() => shown.map((app) => ({ id: app.id, columnId: app.stage.code, app })), [shown]);
  const columns = useMemo(() => stages.map((s) => ({ id: s.code, label: pick(s.label) })), [stages, pick]);

  // Switching view is a step the back button undoes; each keystroke in the filter only replaces the address.
  // The native history calls are synchronous (Next keeps useSearchParams in step with them), so two quick
  // changes can't overtake each other, and each starts from the address as it is now.
  function setUrl(changes: { view?: View; query?: string }) {
    const url = `${pathname}${writeListState(new URLSearchParams(window.location.search), changes)}`;
    if (changes.view !== undefined) window.history.pushState(null, "", url);
    else window.history.replaceState(null, "", url);
  }

  async function moveTo(id: string, stageCode: string) {
    const target = stages.find((s) => s.code === stageCode);
    await move.mutateAsync({ id, stage_code: stageCode }).then(
      () => toast(t("applications.moved", { stage: pick(target?.label) })),
      (e) => {
        toast.error(t("applications.move_failed"));
        throw e;
      },
    );
  }

  const failed = applications.error ?? pack.error;
  const noProfile = profiles.data && profiles.data.length === 0;

  // Top right, beside the title: the count, the search and Board | List (once there's something to find).
  const toolbar = applications.data?.length && pack.data ? (
    <>
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {query && shown.length === 0
          ? t("applications.filter.none", { query })
          : t("applications.count", { count: shown.length })}
      </p>
      <SearchField label={t("applications.filter.label")} placeholder={t(forPack("applications.filter.placeholder", currentPack))}
        defaultValue={query} onChange={(e) => setUrl({ query: e.target.value })} className="w-full sm:w-64" />
      <ViewSwitcher label={t("applications.view")} value={view} onChange={(v) => setUrl({ view: v })}
        options={[{ value: "board", label: t("applications.view.board"), icon: Board },
                  { value: "list", label: t("applications.view.list"), icon: List }]} />
    </>
  ) : null;

  return (
    <div className="space-y-6">
      {beside ? null : <title>{`${t("applications.title")} · apply`}</title>}
      <PageHeader help={<Help slug="applications" />} level={beside ? 2 : 1} title={t("applications.title")} description={t(forPack("applications.description", currentPack))}
        actions={toolbar} />
      {noProfile ? (
        <div className="flex flex-wrap items-center gap-4 rounded-xl border border-primary/40 bg-primary/5 p-4">
          <User className="size-6 text-primary" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{t("applications.no_profile.title")}</p>
            <p className="text-sm text-muted-foreground">{t("applications.no_profile.body")}</p>
          </div>
          <Button asChild><Link href="/profiles/new">{t("applications.no_profile.action")}</Link></Button>
        </div>
      ) : null}
      <PasteBox />
      {failed ? (
        <ErrorNotice message={error((failed as { code?: string }).code)} retryLabel={t("action.retry")}
          onRetry={() => { void applications.refetch(); void pack.refetch(); }} />
      ) : null}
      {applications.data && pack.data ? (
        applications.data.length === 0 ? (
          <EmptyState icon={DocumentAdd} title={t("applications.empty.title")} body={t(forPack("applications.empty.body", currentPack))} />
        ) : (
          <section aria-labelledby="applications-heading" className="space-y-4">
            <h2 id="applications-heading" className="sr-only">{t("applications.count", { count: shown.length })}</h2>
            {view === "list" ? (
              <ApplicationsList applications={shown} pack={pack.data} stages={stages} />
            ) : (
              <KanbanBoard label={t("applications.title")} emptyLabel={t("applications.column.empty")}
                columns={columns} items={items} onMove={moveTo} formatCount={(n) => formatNumber(n, locale)}
                renderCard={(item: { app: Application }) => (
                  <ApplicationCard application={item.app} pack={pack.data!} stages={stages} />
                )} />
            )}
          </section>
        )
      ) : !failed ? (
        <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p>
      ) : null}
    </div>
  );
}
