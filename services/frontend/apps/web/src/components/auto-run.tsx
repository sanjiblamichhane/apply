"use client";

/**
 * One Auto run as a card: the job, where it's up to, why it needs you, and what can be done now. A run that's
 * Ready for you links to the board's form (the person sends it: the extension fills it, they press Submit) and
 * to the application in apply. Runs from before apply stopped sending keep their drafts and screenshots.
 * Stopping offers Undo (start again).
 */
import { type AutoRun, isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { Badge, Button } from "@apply/ui";
import { ExternalLink } from "@apply/ui/icons";
import Link from "next/link";
import { toast } from "sonner";

import { actionsFor, formUrl, useRunAction } from "@/lib/auto";

export function AutoRunCard({ run }: { run: AutoRun }) {
  const { t, error, relative } = useI18n();
  const act = useRunAction();
  const can = actionsFor(run);
  const title = run.opportunity.title || run.opportunity.issuer_name;
  const labels = (run.reason_detail?.labels as string[] | undefined) ?? [];
  const failed = (e: unknown) => toast.error(error(isApiError(e) ? e.code : "INTERNAL"));
  const headingId = `run-${run.id}`;
  const form = run.status === "ready" ? formUrl(run) : null;

  return (
    <li className="space-y-3 rounded-xl border bg-card p-4" aria-labelledby={headingId}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 id={headingId} className="font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">{run.opportunity.issuer_name}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {run.score !== null ? <span className="text-sm font-semibold tabular-nums">{t("auto.fit", { score: run.score })}</span> : null}
          <Badge variant={run.status === "needs_you" ? "destructive" : run.status === "sent" ? "success" : "secondary"}>
            {t(`auto.status.${run.status}`)}
          </Badge>
        </div>
      </div>

      {run.status === "ready" ? <p className="text-sm">{t("auto.how_to_send")}</p> : null}
      {run.status === "sent" && run.finished_at ? <p className="text-sm text-muted-foreground">{relative(run.finished_at)}</p> : null}

      {run.reason ? (
        <div className="space-y-1">
          <p className="text-sm">{error(run.reason)}</p>
          {labels.length ? (
            <>
              <p className="text-sm text-muted-foreground">{t("auto.questions")}</p>
              <ul className="list-disc ps-6 text-sm">{labels.map((l) => <li key={l}>{l}</li>)}</ul>
            </>
          ) : null}
        </div>
      ) : null}

      {run.drafts.length && run.status === "ready" ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">{t("auto.drafts")}</h3>
          <dl className="space-y-2">
            {run.drafts.map((d) => (
              <div key={String(d.label)} className="rounded-md border p-2">
                <dt className="text-sm text-muted-foreground">{String(d.label)}</dt>
                <dd className="text-sm">{String(d.answer)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      {run.screenshots.length ? (
        <ul className="flex flex-wrap gap-2">
          {run.screenshots.map((s) => {
            const label = t("auto.screenshot", { step: t(`auto.step.${s.step}` as "auto.step.dry_run") });
            const href = `/api/v1/auto/runs/${run.id}/screenshots/${s.id}`;
            return (
              <li key={s.id}>
                <a href={href} target="_blank" rel="noreferrer" className="block rounded-md border p-1 focus-visible:outline-2 focus-visible:outline-ring">
                  <img src={href} alt={label} className="h-24 w-36 rounded object-cover object-top" loading="lazy" />
                </a>
              </li>
            );
          })}
        </ul>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {form ? (
          <Button asChild className="gap-2">
            <a href={form} target="_blank" rel="noopener noreferrer">
              {t("auto.open_form")}<span className="sr-only">: {title} {t("auto.new_tab")}</span>
              <ExternalLink aria-hidden className="size-4" />
            </a>
          </Button>
        ) : null}
        {can.review && run.application_id ? (
          <Button asChild variant={run.status === "needs_you" || (run.status === "ready" && !form) ? "default" : "outline"}>
            <Link href={`/applications/${run.application_id}`}>
              {run.status === "needs_you" ? t("auto.open_application") : t("auto.review")}<span className="sr-only">: {title}</span>
            </Link>
          </Button>
        ) : null}
        {can.stop ? (
          <Button variant="ghost" disabled={act.isPending}
            onClick={() => act.mutate({ id: run.id, action: "stop" }, {
              onSuccess: () => toast(t("auto.stopped_toast"), {
                action: { label: t("auto.undo"), onClick: () => act.mutate({ id: run.id, action: "retry" }, { onError: failed }) },
              }),
              onError: failed,
            })}>
            {t("auto.stop")}<span className="sr-only">: {title}</span>
          </Button>
        ) : null}
        {can.retry ? (
          <Button variant="outline" disabled={act.isPending}
            onClick={() => act.mutate({ id: run.id, action: "retry" }, { onSuccess: () => toast(t("auto.trying_again_toast")), onError: failed })}>
            {t("auto.try_again")}
          </Button>
        ) : null}
        {can.dismiss ? (
          <Button variant="ghost" disabled={act.isPending}
            onClick={() => act.mutate({ id: run.id, action: "dismiss" }, { onSuccess: () => toast(t("auto.dismissed_toast")), onError: failed })}>
            {t("auto.dismiss")}
          </Button>
        ) : null}
      </div>
    </li>
  );
}
