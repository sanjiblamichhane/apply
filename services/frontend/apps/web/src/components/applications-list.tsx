"use client";

import type { Application, Pack, Stage } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { ScrollArea, ScrollBar } from "@apply/ui";
import Link from "next/link";

import { DocumentStates } from "./application-card";
import { StageMenu } from "./stage-menu";

/** The same applications as a table: easier to scan, sort by eye, and read with a screen reader. */
export function ApplicationsList({ applications, pack, stages }: { applications: Application[]; pack: Pack; stages: Stage[] }) {
  const { t, pick, relative } = useI18n();
  const stageLabel = (id: string) => pick(stages.find((s) => s.id === id)?.label);
  return (
    // A wide table on a narrow screen scrolls sideways in its own area; the shadows say there's more.
    <ScrollArea className="rounded-xl border bg-card" viewportClassName="scroll-edge-shadows">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{t("applications.title")}</caption>
        <thead className="border-b text-xs text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">{t("applications.column.title")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t(forPack("applications.column.company", pack?.key))}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("applications.column.stage")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("applications.column.documents")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("applications.column.added")}</th>
            <th scope="col" className="px-4 py-3"><span className="sr-only">{t("applications.move")}</span></th>
          </tr>
        </thead>
        <tbody>
          {applications.map((app) => (
            <tr key={app.id} className="border-b last:border-0">
              <th scope="row" className="px-4 py-2 font-medium">
                <Link href={`/applications/${app.id}`} className="inline-flex min-h-11 items-center text-primary underline-offset-4 hover:underline">
                  {app.opportunity.title || t(forPack("applications.card.untitled", app.opportunity.pack))}
                </Link>
              </th>
              <td className="px-4 py-2">{app.opportunity.issuer_name}</td>
              <td className="px-4 py-2">{stageLabel(app.stage.id)}</td>
              <td className="px-4 py-2"><DocumentStates application={app} pack={pack} /></td>
              <td className="px-4 py-2 text-muted-foreground"><time dateTime={app.created_at}>{relative(app.created_at)}</time></td>
              <td className="px-2 py-2 text-right"><StageMenu application={app} stages={stages} compact /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  );
}
