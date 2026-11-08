"use client";

import { isApiError, type Match } from "@apply/api";
import { formatNumber } from "@apply/i18n";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import { Badge, Button } from "@apply/ui";
import { Add, ExternalLink, InProgress, Location, Search, StarFilled, Trash, WarningAlt } from "@apply/ui/icons";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { useCurrentPack } from "@/lib/pack-choice";
import { fitBand, type MatchStatus, useMatches, useMatchStatus, useSourceKinds, useSources, useTrack } from "@/lib/discovery";

const TABS: MatchStatus[] = ["new", "saved", "dismissed", "tracked"];

export default function MatchesPage() {
  return <Suspense><Matches /></Suspense>;
}

export interface MatchActions {
  change: (match: Match, next: "new" | "saved" | "dismissed", message: string) => void;
  track: (match: Match) => void;
  tracking: boolean;
}

function Matches() {
  const { t, error, locale } = useI18n();
  const [currentPack] = useCurrentPack();
  const params = useSearchParams();
  const router = useRouter();
  const tab = (TABS.find((s) => s === params.get("status")) ?? "new") as MatchStatus;
  const matches = useMatches(tab);
  const status = useMatchStatus();
  const tracking = useTrack();

  // The actions live here, not on the card: a card leaves the list the moment it's saved or dismissed, and the
  // confirmation (with its Undo) must still appear after it has gone.
  const actions: MatchActions = {
    change(match, next, message) {
      status.mutate({ id: match.id, status: next, from: tab }, {
        onSuccess: () => {
          toast(message, {
            action: { label: t("action.undo"), onClick: () => status.mutate({ id: match.id, status: tab === "tracked" ? "new" : tab, from: next }) },
          });
        },
        onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")),
      });
    },
    track(match) {
      tracking.mutate(match.id, {
        onSuccess: (result) => {
          toast(t("matches.tracked"));
          router.push(`/applications/${result.application_id}`);
        },
        onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")),
      });
    },
    tracking: tracking.isPending,
  };
  const items = matches.data?.pages.flatMap((p) => p.items) ?? [];
  const counts = matches.data?.pages[0]?.counts;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <title>{`${t("matches.title")} · apply`}</title>
      <PageHeader help={<Help slug="matches" />} title={t("matches.title")} description={t(forPack("matches.description", currentPack))} />
      {/* Tabs are links: each status has its own address, so back and reload keep your place. */}
      <nav aria-label={t("matches.title")} className="flex flex-wrap gap-2">
        {TABS.map((status) => (
          <Link key={status} href={status === "new" ? "/matches" : `/matches?status=${status}`} aria-current={tab === status ? "page" : undefined}
            className={`inline-flex min-h-11 items-center gap-2 rounded-md border px-3 text-sm font-medium ${tab === status ? "border-primary bg-primary/10 text-primary" : "border-input"}`}>
            {t(`matches.tab.${status}`)}
            {counts ? <span className="tabular-nums text-muted-foreground">{formatNumber(counts[status], locale)}</span> : null}
          </Link>
        ))}
      </nav>
      {matches.error ? <ErrorNotice message={error(isApiError(matches.error) ? matches.error.code : "INTERNAL")} retryLabel={t("action.retry")} onRetry={() => matches.refetch()} /> : null}
      {matches.isSuccess && items.length === 0 ? (
        tab === "new" ? (
          <EmptyState icon={StarFilled} title={t("matches.empty.new")} body={t(forPack("matches.empty.body", currentPack))}
            action={<div className="flex flex-wrap justify-center gap-2">
              <Button asChild><Link href="/sources/new" className="gap-2"><Add aria-hidden />{t("sources.new")}</Link></Button>
              <Button asChild variant="outline"><Link href="/searches/new" className="gap-2"><Search aria-hidden />{t("searches.new")}</Link></Button>
            </div>} />
        ) : <p className="text-sm text-muted-foreground">{t("matches.empty.other")}</p>
      ) : null}
      <ol className="space-y-3">
        {items.map((match) => <li key={match.id}><MatchCard match={match} actions={actions} /></li>)}
      </ol>
      {matches.hasNextPage ? (
        <Button variant="outline" onClick={() => matches.fetchNextPage()} disabled={matches.isFetchingNextPage}>{t("action.load_more")}</Button>
      ) : null}
      {matches.isLoading ? <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p> : null}
    </div>
  );
}

function MatchCard({ match, actions }: { match: Match; actions: MatchActions }) {
  const { t, relative, pick } = useI18n();
  const sources = useSources();
  const kinds = useSourceKinds();
  const opp = match.opportunity;
  const attrs = opp.attributes as Record<string, string>;
  const source = sources.data?.find((s) => s.id === opp.source_id);
  const kind = kinds.data?.find((k) => k.kind === source?.kind);
  const change = (next: "new" | "saved" | "dismissed", message: string) => actions.change(match, next, message);

  const words = [...((match.prefilter.keywords as string[] | undefined) ?? [])];
  return (
    <article aria-labelledby={`match-${match.id}`} className="space-y-3 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 id={`match-${match.id}`} className="text-base font-semibold">{opp.title}</h2>
          <p className="text-sm text-muted-foreground">
            {opp.issuer_name}
            {attrs.location ? <> · <Location className="inline size-3.5" aria-hidden /> {attrs.location}</> : null}
          </p>
        </div>
        <Score match={match} />
      </div>

      {opp.status === "closed" ? <Badge variant="muted">{t("matches.closed")}</Badge> : null}
      {match.dealbreakers.length > 0 ? (
        <div className="space-y-1 rounded-lg border border-destructive/60 p-3">
          <p className="flex items-center gap-2 text-sm font-semibold text-destructive"><WarningAlt className="size-4" aria-hidden />{t("matches.dealbreakers")}</p>
          <ul className="list-disc space-y-1 ps-6 text-sm">
            {match.dealbreakers.map((d, i) => (
              <li key={i} lang={d.code ? undefined : "en"}>{d.code === "NO_SPONSORSHIP" ? t("matches.dealbreaker.NO_SPONSORSHIP") : d.text}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {match.score_reasons.length > 0 ? (
        <details className="rounded-lg border p-3">
          <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium">{t("matches.why")}</summary>
          <ul lang="en" className="mt-1 list-disc space-y-1 ps-6 text-sm">{match.score_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </details>
      ) : null}

      <p className="text-xs text-muted-foreground">
        {words.length ? `${t("matches.matched", { words: words.join(", ") })} · ` : ""}
        {opp.posted_at ? <time dateTime={opp.posted_at}>{t("matches.posted", { when: relative(opp.posted_at) })}</time> : null}
        {kind?.attribution && opp.source_url ? (
          <> · <a href={opp.source_url} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-4">{t("matches.via", { source: kind.attribution })}<span className="sr-only"> {t("action.new_tab")}</span></a></>
        ) : source ? <> · {pick(kind?.label)}: {source.name}</> : null}
      </p>

      <div className="flex flex-wrap gap-2">
        {match.status === "tracked" && match.application_id ? (
          <Button asChild><Link href={`/applications/${match.application_id}`}>{t("matches.open_application")}</Link></Button>
        ) : (
          <Button onClick={() => actions.track(match)} disabled={actions.tracking}>{t("matches.track")}</Button>
        )}
        {match.status === "new" ? <Button variant="outline" onClick={() => change("saved", t("matches.saved"))}><StarFilled aria-hidden />{t("matches.save")}</Button> : null}
        {match.status === "saved" ? <Button variant="outline" onClick={() => change("new", t("matches.unsave"))}>{t("matches.unsave")}</Button> : null}
        {match.status === "dismissed" ? <Button variant="outline" onClick={() => change("new", t("matches.restore"))}>{t("matches.restore")}</Button> : null}
        {match.status === "new" || match.status === "saved" ? (
          <Button variant="ghost" className="gap-2" onClick={() => change("dismissed", t("matches.dismissed"))}><Trash aria-hidden />{t("matches.dismiss")}</Button>
        ) : null}
        {opp.apply_url ? (
          <Button asChild variant="ghost" className="gap-2">
            <a href={opp.apply_url} target="_blank" rel="noopener noreferrer"><ExternalLink aria-hidden />{t(forPack("action.open_link", opp.pack))}<span className="sr-only"> {t("action.new_tab")}</span></a>
          </Button>
        ) : null}
      </div>
    </article>
  );
}

function Score({ match }: { match: Match }) {
  const { t, error } = useI18n();
  if (match.score_status === "pending") {
    return <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground"><InProgress className="size-4 animate-spin" aria-hidden />{t("matches.scoring")}</p>;
  }
  if (match.score_status === "capped") return <p className="text-sm text-muted-foreground">{t("matches.capped")}</p>;
  if (match.score === null || match.score === undefined) {
    return <p className="text-sm text-muted-foreground" title={error(match.score_error_code)}>{t("matches.not_scored")}</p>;
  }
  const band = fitBand(match.score);
  return (
    <div className="text-right">
      <p className="text-2xl font-semibold tabular-nums">{t("matches.fit", { score: match.score })}</p>
      <p className={`text-sm font-medium ${band === "strong" ? "text-success" : band === "weak" ? "text-muted-foreground" : "text-foreground"}`}>{t(`matches.fit.${band}`)}</p>
    </div>
  );
}
