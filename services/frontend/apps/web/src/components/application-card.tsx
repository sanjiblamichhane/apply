"use client";

import type { Application, Pack, Stage } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { CheckmarkFilled, CircleFilled, InProgress, Misuse } from "@apply/ui/icons";
import Link from "next/link";

import { type DocumentBadge, documentBadges } from "@/lib/board";

import { StageMenu } from "./stage-menu";

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
}

const BADGE_ICON = { ready: CheckmarkFilled, pending: InProgress, failed: Misuse, none: CircleFilled } as const;

/** A document's state as an icon and words (never colour alone): "Resume ready", "Cover letter: not yet". */
export function DocumentStates({ application, pack }: { application: Application; pack: Pack }) {
  const { pick } = useI18n();
  const types = pack.document_types.filter((d) => d.generatable);
  const badges = documentBadges(application, types.map((d) => d.key));
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
      {types.map((type) => {
        const state: DocumentBadge = badges[type.key] ?? "none";
        const Icon = BADGE_ICON[state];
        return (
          <li key={type.key} className={state === "ready" ? "text-success" : state === "failed" ? "text-destructive" : "text-muted-foreground"}>
            <span className="inline-flex items-center gap-1">
              <Icon className={state === "none" ? "size-2" : "size-3.5"} aria-hidden />
              {pick(type.label)}
              <DocumentStateWord state={state} />
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function DocumentStateWord({ state }: { state: DocumentBadge }) {
  const { t } = useI18n();
  return <span className="sr-only">: {t(`documents.state.${state}`)}</span>;
}

export function ApplicationCard({ application, pack, stages }: { application: Application; pack: Pack; stages: Stage[] }) {
  const { t, relative } = useI18n();
  const opp = application.opportunity;
  const reading = opp.extraction.status === "pending";
  const needsDetails = opp.extraction.status === "manual" && !opp.title;
  const title = opp.title || t(forPack("applications.card.untitled", opp.pack));
  return (
    <article className="relative rounded-xl border bg-card p-3 transition-shadow focus-within:ring-2 focus-within:ring-ring hover:shadow-sm">
      <div className="flex items-start gap-3">
        <div aria-hidden className="grid size-9 shrink-0 place-items-center rounded-lg bg-muted text-xs font-bold text-foreground">
          {initials(opp.issuer_name || title) || "?"}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <h3 className="text-sm font-semibold leading-snug">
            {/* The title's link covers the card, so the whole card opens it; the menu sits above. */}
            <Link href={`/applications/${application.id}`} className="after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none">
              {title}
            </Link>
          </h3>
          {opp.issuer_name ? <p className="truncate text-xs text-muted-foreground">{opp.issuer_name}</p> : null}
          {reading ? <p className="text-xs text-muted-foreground">{t(forPack("applications.card.reading", opp.pack))}</p> : null}
          {needsDetails ? <p className="text-xs font-medium text-destructive">{t("applications.card.needs_details")}</p> : null}
          <DocumentStates application={application} pack={pack} />
          <p className="text-xs text-muted-foreground">
            <time dateTime={application.created_at}>{t("applications.card.added", { when: relative(application.created_at) })}</time>
          </p>
        </div>
        <StageMenu application={application} stages={stages} compact />
      </div>
    </article>
  );
}
