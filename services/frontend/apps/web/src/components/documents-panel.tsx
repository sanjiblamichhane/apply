"use client";

import { type Document, isApiError, type Pack } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Label, ScrollArea, Textarea } from "@apply/ui";
import { CheckmarkFilled, Copy, Download, Edit, InProgress, Renew, View, WarningAlt } from "@apply/ui/icons";
import { useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import { SafeMarkdown } from "@/components/safe-markdown";
import { documentState, downloadName, versions } from "@/lib/documents";
import { useDocuments, useWriteDocument } from "@/lib/queries";
import { PagePreview, PreviewDialog } from "@/components/page-preview";
import { fetchFile, save, useCheckAgain, useEditDocument, useMarkReviewed, useResolveWarning } from "@/lib/review";

/** The documents for one application: one block per kind the model can write. */
export function DocumentsPanel({ applicationId, pack, title }: { applicationId: string; pack: Pack; title: string }) {
  const { t, error } = useI18n();
  const documents = useDocuments(applicationId);
  const types = pack.document_types.filter((d) => d.generatable);
  return (
    <section aria-labelledby="documents-heading" className="space-y-4">
      <div className="flex items-center gap-1"><h2 id="documents-heading" className="text-lg font-semibold">{t("documents.title")}</h2><Help slug="documents" /></div>
      {documents.error ? (
        <ErrorNotice message={error(isApiError(documents.error) ? documents.error.code : "INTERNAL")}
          retryLabel={t("action.retry")} onRetry={() => documents.refetch()} />
      ) : null}
      {types.map((type) => (
        <DocumentBlock key={type.key} applicationId={applicationId} type={type.key} label={type.label}
          documents={documents.data ?? []} loading={documents.isLoading} title={title} />
      ))}
    </section>
  );
}

function DocumentBlock({ applicationId, type, label, documents, loading, title }: {
  applicationId: string; type: string; label: { en: string; ne: string }; documents: Document[]; loading: boolean;
  title: string;
}) {
  const { t, pick, error } = useI18n();
  const write = useWriteDocument(applicationId);
  const state = documentState(documents, type);
  const name = pick(label);
  const current = state.kind === "none" ? null : state.current;
  const older = versions(documents, type).filter((d) => d.id !== current?.id);
  const [editing, setEditing] = useState(false);

  function start() {
    write.mutate(type);
  }

  async function copy(doc: Document) {
    await navigator.clipboard.writeText(doc.content_markdown);
    toast(t("documents.copied"));
  }

  function download(doc: Document) {
    const url = URL.createObjectURL(new Blob([doc.content_markdown], { type: "text/markdown;charset=utf-8" }));
    const link = Object.assign(document.createElement("a"), { href: url, download: downloadName(title, type, doc.version) });
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <article aria-labelledby={`doc-${type}`} className="space-y-3 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`doc-${type}`} className="font-semibold">
          {name}
          {current ? <span className="ms-2 text-sm font-normal text-muted-foreground">{t("documents.version", { version: current.version })}</span> : null}
        </h3>
        {!loading && state.kind !== "pending" ? (
          <Button size="sm" variant={current ? "outline" : "default"} className="gap-2" onClick={start} disabled={write.isPending}>
            <Renew aria-hidden />{current ? t("documents.write_again") : t("documents.write")}
            {/* The visible words first, then what they act on (WCAG 2.5.3: the name contains the label). */}
            <span className="sr-only">: {name}</span>
          </Button>
        ) : null}
      </div>

      <div aria-live="polite">
        {state.kind === "pending" ? (
          <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
            <InProgress className="size-4 animate-spin" aria-hidden />{t("documents.writing")}
          </p>
        ) : null}
        {state.kind === "failed" ? (
          <ErrorNotice message={`${t("documents.failed", { type: name })} ${error(state.failed.error_code)}`}
            retryLabel={t("action.retry")} onRetry={start} />
        ) : null}
      </div>
      {write.error ? <ErrorNotice message={error(isApiError(write.error) ? write.error.code : "INTERNAL")} /> : null}

      {state.kind === "none" && !loading ? <p className="text-sm text-muted-foreground">{t("documents.none")}</p> : null}

      {current ? (
        <div className="space-y-3">
          <Claims applicationId={applicationId} document={current} />
          {editing ? (
            <Editor applicationId={applicationId} document={current} onDone={() => setEditing(false)} />
          ) : (
            <div lang="en" className="space-y-2 rounded-lg border bg-background p-4 text-sm [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_li]:ms-5 [&_li]:list-disc">
              <SafeMarkdown>{current.content_markdown}</SafeMarkdown>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {!editing ? <Button size="sm" variant="outline" className="gap-2" onClick={() => setEditing(true)}><Edit aria-hidden />{t("review.edit")}</Button> : null}
            <Button size="sm" variant="outline" className="gap-2" onClick={() => copy(current)}><Copy aria-hidden />{t("action.copy")}</Button>
            <Button size="sm" variant="outline" className="gap-2" onClick={() => download(current)}><Download aria-hidden />{t("action.download")} (.md)</Button>
            <PreviewButton applicationId={applicationId} document={current} name={name}
              filename={downloadName(title, type, current.version).replace(/\.md$/, "")} />
          </div>
          <Reviewed applicationId={applicationId} document={current} />
          {current.generation_ms ? (
            <p className="text-xs text-muted-foreground">
              {t("documents.written_in", { seconds: t("time.seconds", { count: Math.round(current.generation_ms / 100) / 10 }) })}
              {current.model ? ` · ${current.model}` : ""}
            </p>
          ) : null}
          {older.length > 0 ? (
            <details className="rounded-lg border p-3">
              <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium">{t("documents.versions")}</summary>
              <ul className="mt-2 space-y-3">
                {older.map((doc) => (
                  <li key={doc.id} className="space-y-1">
                    <p className="text-sm font-medium">{t("documents.version", { version: doc.version })}</p>
                    <ScrollArea className="rounded border bg-background" viewportClassName="max-h-60"
                      label={t("documents.version", { version: doc.version })}>
                      <pre lang="en" className="whitespace-pre-wrap p-3 text-xs">{doc.content_markdown}</pre>
                    </ScrollArea>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}


/** What the profile doesn't back up, quoted, with a decision for each: fix it (edit), or "It's true". */
function Claims({ applicationId, document: doc }: { applicationId: string; document: Document }) {
  const { t, error } = useI18n();
  const resolve = useResolveWarning(applicationId);
  const checkAgain = useCheckAgain(applicationId);
  if (doc.claims_status === "pending") {
    return <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground"><InProgress className="size-4 animate-spin" aria-hidden />{t("review.checking")}</p>;
  }
  const open = doc.claim_warnings.filter((w) => !w.resolved);
  return (
    <div className="space-y-2">
      {doc.claims_status === "failed" ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <WarningAlt className="size-4 text-destructive" aria-hidden />
          <span className="flex-1">{t("review.check_failed")}</span>
          <Button size="sm" variant="outline" onClick={() => checkAgain.mutate(doc.id)} disabled={checkAgain.isPending}>{t("review.check_again")}</Button>
        </div>
      ) : null}
      {doc.claims_status === "checked" && doc.claim_warnings.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-success"><CheckmarkFilled className="size-4" aria-hidden />{t("review.all_clear")}</p>
      ) : null}
      {doc.claim_warnings.length > 0 ? (
        <div className="space-y-2 rounded-lg border border-destructive/60 p-3">
          <h4 className="flex items-center gap-2 text-sm font-semibold">
            <WarningAlt className="size-4 text-destructive" aria-hidden />{t("review.warnings")}
            <span className="font-normal text-muted-foreground">{t("review.warnings_count", { count: open.length })}</span>
          </h4>
          <ul className="divide-y">
            {doc.claim_warnings.map((w) => (
              <li key={w.id} className="flex flex-wrap items-start gap-3 py-2">
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">{t(`review.kind.${w.kind}`)}</p>
                  <p lang="en" className="text-sm"><mark className="rounded bg-muted px-1 text-foreground">{w.quote}</mark></p>
                  <p lang="en" className="text-sm text-muted-foreground">{w.reason}</p>
                </div>
                {w.resolved === "kept" ? (
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 text-sm text-success"><CheckmarkFilled className="size-4" aria-hidden />{t("review.kept")}</span>
                    <Button size="sm" variant="ghost" onClick={() => resolve.mutate({ documentId: doc.id, warningId: w.id, resolution: "open" })}>{t("review.reopen")}</Button>
                  </div>
                ) : w.kind !== "confirm" ? (
                  <Button size="sm" variant="outline" onClick={() => resolve.mutate({ documentId: doc.id, warningId: w.id, resolution: "kept" })}>
                    {t("review.keep")}<span className="sr-only">: {w.quote}</span>
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {resolve.error ? <ErrorNotice message={error(isApiError(resolve.error) ? resolve.error.code : "INTERNAL")} /> : null}
    </div>
  );
}

function Editor({ applicationId, document: doc, onDone }: { applicationId: string; document: Document; onDone: () => void }) {
  const { t, error } = useI18n();
  const edit = useEditDocument(applicationId);
  const [text, setText] = useState(doc.content_markdown);
  const id = `editor-${doc.id}`;
  return (
    <form className="space-y-2" onSubmit={(e) => {
      e.preventDefault();
      edit.mutate({ documentId: doc.id, content: text }, {
        onSuccess: (saved) => {
          toast(t("review.saved_version", { version: saved.version }));
          onDone();
        },
      });
    }}>
      <Label htmlFor={id}>{t("review.edit")}</Label>
      <p id={`${id}-hint`} className="text-sm text-muted-foreground">{t("review.editing_hint")}</p>
      <Textarea id={id} lang="en" rows={18} value={text} onChange={(e) => setText(e.target.value)} aria-describedby={`${id}-hint`}
        className="font-mono text-sm" />
      {edit.error ? <ErrorNotice message={error(isApiError(edit.error) ? edit.error.code : "INTERNAL")} /> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={edit.isPending || !text.trim() || text === doc.content_markdown}>{edit.isPending ? t("action.saving") : t("review.save_version")}</Button>
        <Button type="button" variant="outline" onClick={onDone}>{t("action.cancel")}</Button>
      </div>
    </form>
  );
}

/**
 * The version in the person's template, as it will be downloaded: previewed first, then saved as a PDF (the page
 * printed) or as the page itself.
 */
function PreviewButton({ applicationId, document: doc, name, filename }: {
  applicationId: string; document: Document; name: string; filename: string;
}) {
  const { t, error } = useI18n();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<string | null>(null);
  const [busy, setBusy] = useState<"" | "pdf" | "html">("");
  const title = `${name}, ${t("documents.version", { version: doc.version })}`;

  async function show() {
    setOpen(true);
    setPage(null);
    try {
      setPage(await (await fetchFile(applicationId, doc.id, "html")).text());
    } catch (e) {
      setOpen(false);
      toast.error(error(isApiError(e) ? e.code : "INTERNAL"));
    }
  }

  async function download(kind: "pdf" | "html") {
    setBusy(kind);
    try {
      save(await fetchFile(applicationId, doc.id, kind), `${filename}.${kind}`);
    } catch (e) {
      toast.error(error(isApiError(e) ? e.code : "INTERNAL"));
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <Button size="sm" variant="outline" className="gap-2" onClick={show}>
        <View aria-hidden />{t("documents.preview")}<span className="sr-only">: {name}</span>
      </Button>
      <PreviewDialog open={open} onOpenChange={setOpen} title={title} description={t("documents.preview_hint")}
        actions={page !== null ? (
          <>
            <Button variant="outline" className="gap-2" onClick={() => download("html")} disabled={busy !== ""}>
              <Download aria-hidden />{t("documents.download_html")}
            </Button>
            <Button className="gap-2" onClick={() => download("pdf")} disabled={busy !== ""}>
              <Download aria-hidden />{busy === "pdf" ? t("review.pdf_making") : t("documents.download_pdf")}
            </Button>
          </>
        ) : null}>
        {page === null ? (
          <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
            <InProgress className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />{t("documents.preview_making")}
          </p>
        ) : (
          <PagePreview html={page} title={t("documents.preview_frame", { type: title })} />
        )}
      </PreviewDialog>
    </>
  );
}

function Reviewed({ applicationId, document: doc }: { applicationId: string; document: Document }) {
  const { t, relative } = useI18n();
  const mark = useMarkReviewed(applicationId);
  // Immediate feedback: the box shows what was asked for the moment it's clicked, and goes back if saving fails.
  const saved = Boolean(doc.reviewed_at);
  const [checked, setChecked] = useState(saved);
  const [seen, setSeen] = useState(saved);
  if (saved !== seen) {
    setSeen(saved);
    setChecked(saved);
  }
  return (
    <label className="flex min-h-11 items-center gap-3 text-sm">
      <input type="checkbox" className="size-5 accent-[var(--primary)]" checked={checked}
        onChange={(e) => {
          const next = e.target.checked;
          setChecked(next);
          mark.mutate({ documentId: doc.id, reviewed: next }, { onError: () => setChecked(saved) });
        }} />
      <span>
        {t("review.mark_reviewed")}
        {doc.reviewed_at ? <span className="text-muted-foreground"> · {t("review.reviewed", { when: relative(doc.reviewed_at) })}</span> : null}
      </span>
    </label>
  );
}
