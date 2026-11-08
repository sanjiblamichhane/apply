"use client";

import { isApiError, type Source } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogTitle, AlertDialogTrigger, Badge, Button,
} from "@apply/ui";
import { Add, CheckmarkFilled, InProgress, List, PauseOutline, Renew, Trash, WarningAlt } from "@apply/ui/icons";
import Link from "next/link";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { useCurrentPack } from "@/lib/pack-choice";
import { useDeleteSource, useFetchSource, useSourceKinds, useSources, useUpdateSource } from "@/lib/discovery";

export default function SourcesPage() {
  const { t, error } = useI18n();
  const [currentPack] = useCurrentPack();
  const sources = useSources();
  const kinds = useSourceKinds();
  // A pack with no sources (contracts) offers nothing to add: its empty state says to paste instead.
  const add = kinds.data?.length === 0 ? null : <Button asChild className="gap-2"><Link href="/sources/new"><Add aria-hidden />{t("sources.new")}</Link></Button>;
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <title>{`${t("sources.title")} · apply`}</title>
      <PageHeader help={<Help slug="sources" />} title={t("sources.title")} description={t(forPack("sources.description", currentPack))} actions={add} />
      {sources.error ? <ErrorNotice message={error((sources.error as { code?: string }).code)} retryLabel={t("action.retry")} onRetry={() => sources.refetch()} /> : null}
      {sources.data?.length === 0 ? <EmptyState icon={List} title={t("sources.empty.title")} body={t(forPack("sources.empty.body", currentPack))} action={add} /> : null}
      <ul className="space-y-3">
        {(sources.data ?? []).map((source) => <li key={source.id}><SourceRow source={source} /></li>)}
      </ul>
    </div>
  );
}

function SourceRow({ source }: { source: Source }) {
  const { t, error, pick, relative } = useI18n();
  const [currentPack] = useCurrentPack();
  const kinds = useSourceKinds();
  const fetchNow = useFetchSource();
  const update = useUpdateSource();
  const remove = useDeleteSource();
  const kind = kinds.data?.find((k) => k.kind === source.kind);
  const checking = source.enabled && source.last_status === "never";

  return (
    <article aria-labelledby={`source-${source.id}`} className="space-y-3 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={`source-${source.id}`} className="font-semibold">{source.name}</h2>
          <p className="text-sm text-muted-foreground">{pick(kind?.label)}</p>
        </div>
        {!source.enabled ? <Badge variant="muted"><PauseOutline className="size-3" aria-hidden />{t("sources.paused")}</Badge> : null}
      </div>
      <p aria-live="polite" className="flex items-center gap-2 text-sm">
        {checking ? <><InProgress className="size-4 animate-spin" aria-hidden />{t("sources.fetching")}</>
          : source.last_status === "ok" && source.last_fetched_at
            ? <><CheckmarkFilled className="size-4 text-success" aria-hidden />{t(forPack("sources.ok", currentPack), { count: source.last_count, when: relative(source.last_fetched_at) })}</>
            : source.last_status === "failed" && source.last_fetched_at
              ? <><WarningAlt className="size-4 text-destructive" aria-hidden /><span>{t("sources.failed", { when: relative(source.last_fetched_at) })}: {error(source.last_error_code)}</span></>
              : t("sources.never")}
      </p>
      {kind ? <p className="text-xs text-muted-foreground">{t("sources.terms")}: {pick(kind.terms)}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" className="gap-2" disabled={fetchNow.isPending || checking || !source.enabled}
          onClick={() => fetchNow.mutate(source.id, { onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")) })}>
          <Renew aria-hidden />{t("sources.fetch")}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => update.mutate({ id: source.id, enabled: !source.enabled })}>
          {source.enabled ? t("sources.pause") : t("sources.resume")}
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild><Button variant="ghost" size="sm" className="gap-2"><Trash aria-hidden />{t("action.remove")}</Button></AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogTitle>{t("sources.delete_confirm.title")}</AlertDialogTitle>
            <AlertDialogDescription>{t(forPack("sources.delete_confirm.body", currentPack))}</AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogCancel>{t("action.cancel")}</AlertDialogCancel>
              <AlertDialogAction onClick={() => remove.mutate(source.id, { onSuccess: () => toast(t("sources.deleted")) })}>{t("action.remove")}</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </article>
  );
}
