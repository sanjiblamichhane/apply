"use client";

import { isApiError, type TemplateCheck, type TemplateKind } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button } from "@apply/ui";
import { CheckmarkFilled, Download, Reset, Upload, View, WarningAlt } from "@apply/ui/icons";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import { PagePreview, PreviewDialog } from "./page-preview";
import { useCurrentPack } from "@/lib/pack-choice";
import { usePack } from "@/lib/queries";
import { save } from "@/lib/review";
import { checkTemplate, defaultTemplate, useResetTemplate, useSaveTemplate, useTemplate } from "@/lib/templates";

const KINDS: TemplateKind[] = ["sections", "letter"];
const MAX_BYTES = 256 * 1024;

/** Settings → Document templates: the two the person's documents are made in, each theirs to change. */
export function TemplatesSection() {
  const { t } = useI18n();
  return (
    <section aria-labelledby="templates-heading" className="space-y-3 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-1">
        <h2 id="templates-heading" className="text-lg font-semibold">{t("templates.title")}</h2>
        <Help slug="documents" />
      </div>
      <p className="text-sm text-muted-foreground">{t("templates.hint")}</p>
      <ul className="divide-y">
        {KINDS.map((kind) => <TemplateRow key={kind} kind={kind} />)}
      </ul>
    </section>
  );
}

/** What this kind is called in the pack in use ("Resume", "Cover letter"), else in general. */
function useKindName(kind: TemplateKind): string {
  const { t, pick } = useI18n();
  const [packKey] = useCurrentPack();
  const pack = usePack(packKey);
  const names = (pack.data?.document_types ?? []).filter((d) => d.generatable && d.layout === kind).map((d) => pick(d.label));
  return names.length ? new Intl.ListFormat(undefined, { type: "conjunction" }).format(names) : t(`templates.${kind}`);
}

function TemplateRow({ kind }: { kind: TemplateKind }) {
  const { t, error } = useI18n();
  const name = useKindName(kind);
  const template = useTemplate(kind);
  const saveTemplate = useSaveTemplate(kind);
  const reset = useResetTemplate(kind);
  const input = useRef<HTMLInputElement>(null);
  const [previewing, setPreviewing] = useState(false);
  const [checking, setChecking] = useState<{ filename: string; html: string; result: TemplateCheck } | null>(null);
  const current = template.data;

  async function upload(file: File) {
    if (!/\.html?$/i.test(file.name) || file.size > MAX_BYTES) {
      toast.error(t("templates.not_html"));
      return;
    }
    const html = await file.text();
    try {
      setChecking({ filename: file.name, html, result: await checkTemplate(kind, html) });
    } catch (e) {
      toast.error(error(isApiError(e) ? e.code : "INTERNAL"));
    }
  }

  function use() {
    if (!checking) return;
    saveTemplate.mutate({ html: checking.html, filename: checking.filename }, {
      onSuccess: () => {
        setChecking(null);
        toast(t("templates.saved"));
      },
    });
  }

  function backToDefault() {
    if (!current?.custom) return;
    const mine = { html: current.html, filename: current.filename };
    // Forgiving: the template that was in use comes back with Undo, rather than a "Are you sure?" first.
    reset.mutate(undefined, {
      onSuccess: () => toast(t("templates.reset_done"), {
        action: { label: t("templates.undo"), onClick: () => saveTemplate.mutate(mine) },
      }),
    });
  }

  async function downloadDefault() {
    const found = await defaultTemplate(kind);
    save(new Blob([found.html], { type: "text/html;charset=utf-8" }), `${kind}.html`);
  }

  return (
    <li className="space-y-2 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">{name}</h3>
        {current ? (
          <p className="text-sm text-muted-foreground">
            {current.custom ? t("templates.yours", { file: current.filename }) : t("templates.default")}
          </p>
        ) : null}
      </div>
      {template.error ? (
        <ErrorNotice message={error(isApiError(template.error) ? template.error.code : "INTERNAL")}
          retryLabel={t("action.retry")} onRetry={() => template.refetch()} />
      ) : null}
      {current ? (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" className="gap-2" onClick={() => setPreviewing(true)}>
            <View aria-hidden />{t("documents.preview")}<span className="sr-only">: {name}</span>
          </Button>
          <Button size="sm" variant="outline" className="gap-2"
            onClick={() => save(new Blob([current.html], { type: "text/html;charset=utf-8" }), current.filename)}>
            <Download aria-hidden />{t("templates.download")}<span className="sr-only">: {name}</span>
          </Button>
          {/* The button opens the file picker; the input itself isn't shown or reached (one control, not two). */}
          <input ref={input} type="file" accept=".html,.htm,text/html" hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void upload(file);
            }} />
          <Button size="sm" variant="outline" className="gap-2" onClick={() => input.current?.click()}>
            <Upload aria-hidden />{t("templates.upload")}<span className="sr-only">: {name}</span>
          </Button>
          {current.custom ? (
            <>
              <Button size="sm" variant="ghost" className="gap-2" onClick={downloadDefault}>
                <Download aria-hidden />{t("templates.download_default")}<span className="sr-only">: {name}</span>
              </Button>
              <Button size="sm" variant="ghost" className="gap-2" onClick={backToDefault} disabled={reset.isPending}>
                <Reset aria-hidden />{t("templates.use_default")}<span className="sr-only">: {name}</span>
              </Button>
            </>
          ) : null}
        </div>
      ) : null}

      {current ? (
        <PreviewDialog open={previewing} onOpenChange={setPreviewing} title={t("templates.preview_title", { kind: name })}
          description={t("templates.preview_hint")}>
          <PagePreview html={current.preview_html} title={t("templates.preview_title", { kind: name })} />
        </PreviewDialog>
      ) : null}

      {checking ? (
        <PreviewDialog open onOpenChange={(open) => { if (!open) setChecking(null); }}
          title={t("templates.check_title", { file: checking.filename })}
          description={checking.result.problems.length ? t("templates.problems", { count: checking.result.problems.length }) : t("templates.passed")}
          actions={
            <>
              <Button variant="outline" onClick={() => input.current?.click()}>{t("templates.choose_another")}</Button>
              {checking.result.problems.length === 0 ? (
                <Button onClick={use} disabled={saveTemplate.isPending}>{t("templates.use")}</Button>
              ) : null}
            </>
          }>
          {checking.result.problems.length ? (
            <ul className="space-y-2" aria-label={t("templates.problems", { count: checking.result.problems.length })}>
              {checking.result.problems.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <WarningAlt className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
                  <span>
                    <span lang="en">{p.message}</span>
                    {p.wcag ? <span className="ms-2 text-muted-foreground">{t("templates.wcag", { sc: p.wcag })}</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <>
              <p className="flex items-center gap-2 text-sm text-success"><CheckmarkFilled className="size-4" aria-hidden />{t("templates.passed")}</p>
              <PagePreview html={checking.result.preview_html} title={t("templates.preview_title", { kind: name })} />
            </>
          )}
          {saveTemplate.error ? <ErrorNotice message={error(isApiError(saveTemplate.error) ? saveTemplate.error.code : "INTERNAL")} /> : null}
        </PreviewDialog>
      ) : null}
    </li>
  );
}
