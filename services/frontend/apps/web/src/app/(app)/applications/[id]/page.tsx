"use client";

import { isApiError } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Label, Textarea } from "@apply/ui";
import { ArrowLeft, ExternalLink, X } from "@apply/ui/icons";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { DeleteApplication } from "@/components/delete-application";
import { DocumentsPanel } from "@/components/documents-panel";
import { KitPanel } from "@/components/kit-panel";
import { OpportunityPanel } from "@/components/opportunity-panel";
import { StageMenu } from "@/components/stage-menu";
import { boardStages } from "@/lib/board";
import { useApplication, useHistory, useOpportunity, usePack, useUpdateApplication } from "@/lib/queries";

export default function ApplicationPage() {
  const { id } = useParams<{ id: string }>();
  const { t, error } = useI18n();
  const application = useApplication(id);
  const opportunity = useOpportunity(application.data?.opportunity.id);
  const pack = usePack(application.data?.opportunity.pack ?? "job");

  if (application.error) {
    const code = isApiError(application.error) ? application.error.code : "INTERNAL";
    return (
      <div className="space-y-4">
        <BackLink />
        <ErrorNotice message={error(code)} retryLabel={code === "APPLICATION_NOT_FOUND" ? undefined : t("action.retry")}
          onRetry={() => application.refetch()} />
      </div>
    );
  }
  if (!application.data || !pack.data) {
    return <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p>;
  }

  const app = application.data;
  const opp = opportunity.data;
  const title = opp?.title || app.opportunity.title || t(forPack("applications.card.untitled", app.opportunity.pack));
  const company = opp?.issuer_name || app.opportunity.issuer_name;
  const stages = boardStages(pack.data.pipeline.stages);

  return (
    <div className="space-y-6">
      <title>{`${title} · apply`}</title>
      <BackLink />
      <header className="space-y-3">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1 space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {company ? <p className="text-muted-foreground">{company}</p> : null}
          </div>
          <CloseLink title={title} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StageMenu application={app} stages={pack.data.pipeline.stages} />
          {app.opportunity.apply_url ? (
            <Button asChild variant="ghost" className="gap-2">
              <a href={app.opportunity.apply_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink aria-hidden />{t(forPack("action.open_link", app.opportunity.pack))}
                <span className="sr-only"> {t("action.new_tab")}</span>
              </a>
            </Button>
          ) : null}
          <DeleteApplication application={app} title={title} />
        </div>
      </header>

      <DocumentsPanel applicationId={app.id} pack={pack.data} title={title} />
      <KitPanel applicationId={app.id} />
      {opp ? <OpportunityPanel opportunity={opp} /> : null}
      <History applicationId={app.id} stages={stages} />
      <Notes applicationId={app.id} initial={app.notes} />
    </div>
  );
}

/** Beside the board (wide screens), the detail closes with ✕, back to the board alone; narrower, BackLink does. */
function CloseLink({ title }: { title: string }) {
  const { t } = useI18n();
  return (
    <Link href="/applications" aria-label={`${t("application.close")}: ${title}`}
      className="-me-2 -mt-1 hidden size-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring xl:inline-flex">
      <X className="size-5" aria-hidden />
    </Link>
  );
}

function BackLink() {
  const { t } = useI18n();
  return (
    <Link href="/applications" className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-primary underline-offset-4 hover:underline xl:hidden">
      <ArrowLeft className="size-4" aria-hidden />{t("application.back")}
    </Link>
  );
}

function History({ applicationId, stages }: { applicationId: string; stages: { id: string; label: { en: string; ne: string } }[] }) {
  const { t, pick, date } = useI18n();
  const history = useHistory(applicationId);
  if (!history.data?.length) return null;
  const label = (id: string) => pick(stages.find((s) => s.id === id)?.label);
  return (
    <section aria-labelledby="history-heading" className="space-y-3 rounded-xl border bg-card p-4">
      <h2 id="history-heading" className="text-lg font-semibold">{t("application.history")}</h2>
      <ol className="space-y-3">
        {history.data.map((entry) => (
          <li key={entry.id} className="border-s-2 border-input ps-3 text-sm">
            <p className="font-medium">{t("application.history.entered", { stage: label(entry.stage.id) })}</p>
            <p className="text-muted-foreground">
              <time dateTime={entry.entered_at}>{date(entry.entered_at, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" })}</time>
            </p>
            {entry.note ? <p>{entry.note}</p> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}

function Notes({ applicationId, initial }: { applicationId: string; initial: string }) {
  const { t, error } = useI18n();
  const update = useUpdateApplication(applicationId);
  const [notes, setNotes] = useState(initial);
  return (
    <section aria-labelledby="notes-heading" className="space-y-3 rounded-xl border bg-card p-4">
      <h2 id="notes-heading" className="text-lg font-semibold">
        <Label htmlFor="notes" className="text-lg font-semibold">{t("application.notes")}</Label>
      </h2>
      <Textarea id="notes" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
      {update.error ? <ErrorNotice message={error(isApiError(update.error) ? update.error.code : "INTERNAL")} /> : null}
      <Button variant="outline" disabled={notes === initial || update.isPending}
        onClick={() => update.mutate({ notes }, { onSuccess: () => toast(t("state.saved")) })}>
        {update.isPending ? t("action.saving") : t("action.save")}
      </Button>
    </section>
  );
}
