"use client";

import { isApiError } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Badge, Button, Label, Textarea } from "@apply/ui";
import { CheckmarkFilled, Copy, ExternalLink, WarningAlt } from "@apply/ui/icons";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import { answerText, useKit, useSubmit, useUndoSubmission } from "@/lib/review";

/** Applying by hand, in order: the form, the documents, the answers, then "I've submitted it" (HIG: one task, in steps). */
export function KitPanel({ applicationId }: { applicationId: string }) {
  const { t, pick, error, relative, locale } = useI18n();
  const kit = useKit(applicationId);
  const submit = useSubmit(applicationId);
  const undo = useUndoSubmission(applicationId);
  const [note, setNote] = useState("");
  if (kit.error) return <ErrorNotice message={error(isApiError(kit.error) ? kit.error.code : "INTERNAL")} />;
  if (!kit.data) return null;
  const data = kit.data;
  const latest = data.submissions.find((s) => !s.undone_at);
  const answered = data.answers.filter((a) => a.answer && !(a.is_sensitive && a.answer === "decline"));

  async function copy(text: string) {
    await navigator.clipboard.writeText(text);
    toast(t("documents.copied"));
  }

  return (
    <section aria-labelledby="kit-heading" className="space-y-4 rounded-xl border bg-card p-4">
      <div>
        <div className="flex items-center gap-1"><h2 id="kit-heading" className="text-lg font-semibold">{t("kit.title")}</h2><Help slug="kit" /></div>
        <p className="text-sm text-muted-foreground">{t("kit.description")}</p>
      </div>
      <ol className="space-y-4">
        <li className="space-y-2">
          <h3 className="font-medium">1. {t("kit.step.open")}</h3>
          {data.apply_url ? (
            <Button asChild variant="outline" className="gap-2">
              <a href={data.apply_url} target="_blank" rel="noopener noreferrer"><ExternalLink aria-hidden />{t(forPack("action.open_link", data.application.opportunity.pack))}<span className="sr-only"> {t("action.new_tab")}</span></a>
            </Button>
          ) : <p className="text-sm text-muted-foreground">{t("kit.step.open_none")}</p>}
        </li>
        <li className="space-y-2">
          <h3 className="font-medium">2. {t("kit.step.documents")}</h3>
          {data.documents.length === 0 ? <p className="text-sm text-muted-foreground">{t("kit.step.documents_none")}</p> : (
            <ul className="space-y-1">
              {data.documents.map((d) => (
                <li key={d.document.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium">{pick(d.label)}</span>
                  <span className="text-muted-foreground">{t("documents.version", { version: d.document.version })}</span>
                  {d.open_warnings > 0 ? <Badge variant="outline" className="gap-1 border-destructive/60"><WarningAlt className="size-3 text-destructive" aria-hidden />{t("kit.open_warnings", { count: d.open_warnings })}</Badge> : null}
                  {d.document.reviewed_at ? <Badge variant="success"><CheckmarkFilled className="size-3" aria-hidden />{t("review.reviewed", { when: relative(d.document.reviewed_at) })}</Badge>
                    : <Badge variant="muted">{t("kit.not_reviewed")}</Badge>}
                </li>
              ))}
            </ul>
          )}
        </li>
        <li className="space-y-2">
          <h3 className="font-medium">3. {t("kit.step.answers")}</h3>
          <p className="text-sm text-muted-foreground">{t("kit.step.answers_hint")} <Link href="/answers" className="text-primary underline underline-offset-4">{t("answers.title")}</Link></p>
          <dl className="divide-y rounded-lg border">
            {answered.map((a) => {
              const text = answerText(a, { yes: t("answers.yes"), no: t("answers.no") }, locale);
              return (
                // dt and dd straight inside the group, as a <dl> needs; the Copy button is the second column.
                <div key={a.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 px-3 py-2">
                  <dt className="text-sm text-muted-foreground">{pick(a.question)}</dt>
                  <dd className="col-start-1 text-sm font-medium">{text}</dd>
                  <dd className="col-start-2 row-span-2 row-start-1">
                    <Button size="icon" variant="ghost" aria-label={`${t("action.copy")}: ${pick(a.question)}`} onClick={() => copy(text)}><Copy aria-hidden /></Button>
                  </dd>
                </div>
              );
            })}
          </dl>
        </li>
        <li className="space-y-2">
          <h3 className="font-medium">4. {t("kit.step.submit")}</h3>
          {latest ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="flex items-center gap-2 text-sm text-success" role="status"><CheckmarkFilled className="size-4" aria-hidden />{t("kit.submitted", { when: relative(latest.submitted_at) })} {t(`kit.channel.${latest.channel}`)}</p>
              <Button size="sm" variant="ghost" onClick={() => undo.mutate(latest.id, {
                onSuccess: () => toast(t("kit.undone")),
                onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")),
              })}>{t("kit.undo")}</Button>
            </div>
          ) : (
            <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); submit.mutate(note); }}>
              <Label htmlFor="kit-note">{t("kit.note")}</Label>
              <Textarea id="kit-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
              {submit.error ? <ErrorNotice message={error(isApiError(submit.error) ? submit.error.code : "INTERNAL")} /> : null}
              <Button type="submit" disabled={submit.isPending}>{t("kit.submit")}</Button>
            </form>
          )}
        </li>
      </ol>
    </section>
  );
}
