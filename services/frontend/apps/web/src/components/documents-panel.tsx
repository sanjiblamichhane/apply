"use client";

import { type Document, isApiError, type Pack } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label, ScrollArea, Textarea } from "@apply/ui";
import { CheckmarkFilled, Copy, Download, Edit, InProgress, Renew, View, WarningAlt } from "@apply/ui/icons";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import { SafeMarkdown } from "@/components/safe-markdown";
import { documentState, downloadName, versions } from "@/lib/documents";
import { useDocuments, useWriteDocument } from "@/lib/queries";
import { PagePreview, PreviewDialog } from "@/components/page-preview";
import { fetchFile, save, useCheckAgain, useEditDocument, useMarkReviewed, useResolveWarning, useRewrite } from "@/lib/review";

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
          {current ? (
            <span className="ms-2 text-sm font-normal text-muted-foreground">
              {t("documents.version", { version: current.version })}
              {current.source === "edited" || current.source === "rewritten" ? ` · ${t(`review.source.${current.source}`)}` : null}
            </span>
          ) : null}
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
          {!editing && state.kind !== "pending" ? <Rewrite applicationId={applicationId} document={current} name={name} /> : null}
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


type Warning = Document["claim_warnings"][number];

/**
 * What the profile doesn't back up, in its sentence, with a decision for each: "It's true", or "It's wrong" and
 * what's true instead (a marker left to fill in: what it should say). The corrections go into a rewrite.
 */
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
              <ClaimItem key={w.id} warning={w} busy={resolve.isPending}
                onResolve={(resolution, correction) => resolve.mutate({ documentId: doc.id, warningId: w.id, resolution, correction })} />
            ))}
          </ul>
        </div>
      ) : null}
      {resolve.error ? <ErrorNotice message={error(isApiError(resolve.error) ? resolve.error.code : "INTERNAL")} /> : null}
    </div>
  );
}

function ClaimItem({ warning: w, busy, onResolve }: {
  warning: Warning; busy: boolean; onResolve: (resolution: "kept" | "wrong" | "open", correction?: string) => void;
}) {
  const { t } = useI18n();
  const [correcting, setCorrecting] = useState(false);
  const [text, setText] = useState(w.correction ?? "");
  const marker = w.kind === "confirm";
  const id = `correction-${w.id}`;
  // The field takes focus when the person opens it; Cancel puts focus back on the button that opened it.
  const field = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const opened = useRef(false);
  useEffect(() => {
    if (correcting) field.current?.focus();
    else if (opened.current) opener.current?.focus();
    opened.current = correcting;
  }, [correcting]);
  // After a decision, the buttons change: focus goes to the first of the new ones, not back to the page.
  const item = useRef<HTMLLIElement>(null);
  const decided = useRef(false);
  const decide = (resolution: "kept" | "wrong" | "open", correction?: string) => {
    decided.current = true;
    onResolve(resolution, correction);
  };
  useEffect(() => {
    if (!decided.current) return;
    decided.current = false;
    item.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, [w.resolved, w.correction]);
  return (
    <li ref={item} className="space-y-2 py-2">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-xs font-medium text-muted-foreground">{t(`review.kind.${w.kind}`)}</p>
          <p lang="en" className="text-sm"><InSentence sentence={w.sentence} quote={w.quote} /></p>
          <p lang="en" className="text-sm text-muted-foreground">{w.reason}</p>
        </div>
        {w.resolved ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-sm text-success">
              <CheckmarkFilled className="size-4 shrink-0" aria-hidden />
              {w.resolved === "kept" ? t("review.kept")
                : !w.correction ? t("review.take_out_said")
                : t(marker ? "review.filled_said" : "review.wrong_said", { correction: w.correction })}
            </span>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => { setText(w.correction ?? ""); decide("open"); }}>
              {t("review.reopen")}<span className="sr-only">: {w.quote}</span>
            </Button>
          </div>
        ) : !correcting ? (
          <div className="flex flex-wrap gap-2">
            {!marker ? (
              <Button size="sm" variant="outline" disabled={busy} onClick={() => decide("kept")}>
                {t("review.keep")}<span className="sr-only">: {w.quote}</span>
              </Button>
            ) : null}
            <Button ref={opener} size="sm" variant="outline" disabled={busy} onClick={() => setCorrecting(true)}>
              {t(marker ? "review.fill_in" : "review.wrong")}<span className="sr-only">: {w.quote}</span>
            </Button>
          </div>
        ) : null}
      </div>
      {correcting && !w.resolved ? (
        <form className="space-y-2" onSubmit={(e) => {
          e.preventDefault();
          opened.current = false; // the decision moves focus, not Cancel's rule
          decide("wrong", text.trim());
          setCorrecting(false);
        }}>
          <Label htmlFor={id}>{t(marker ? "review.fill_label" : "review.correction_label")}</Label>
          <p id={`${id}-hint`} className="text-sm text-muted-foreground">{t("review.correction_hint")}</p>
          <Input ref={field} id={id} lang="en" maxLength={500} value={text} onChange={(e) => setText(e.target.value)}
            aria-describedby={`${id}-hint`} />
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={busy}>{t("action.save")}</Button>
            <Button type="button" size="sm" variant="outline" onClick={() => setCorrecting(false)}>{t("action.cancel")}</Button>
          </div>
        </form>
      ) : null}
    </li>
  );
}

/** The sentence a warning is in, its words marked; the words alone for a warning checked before sentences. */
function InSentence({ sentence, quote }: { sentence?: string | null; quote: string }) {
  const at = sentence ? sentence.toLowerCase().indexOf(quote.toLowerCase()) : -1;
  const mark = (words: string) => <mark className="rounded bg-muted px-1 font-medium text-foreground underline decoration-destructive decoration-2 underline-offset-2">{words}</mark>;
  if (!sentence || at < 0) return mark(quote);
  return <>{sentence.slice(0, at)}{mark(sentence.slice(at, at + quote.length))}{sentence.slice(at + quote.length)}</>;
}

/**
 * Write it again with the person's changes: their corrections on the warnings, and anything else they say. Open
 * while there are corrections; a disclosure otherwise.
 */
function Rewrite({ applicationId, document: doc, name }: { applicationId: string; document: Document; name: string }) {
  const { t, error } = useI18n();
  const rewrite = useRewrite(applicationId);
  const corrections = doc.claim_warnings.filter((w) => w.resolved === "wrong").length;
  const [asked, setAsked] = useState(false);
  const [notes, setNotes] = useState("");
  const id = `rewrite-${doc.id}`;
  if (corrections === 0 && !asked) {
    return (
      <Button size="sm" variant="ghost" className="gap-2" onClick={() => setAsked(true)}>
        <Edit aria-hidden />{t("review.rewrite_open")}<span className="sr-only">: {name}</span>
      </Button>
    );
  }
  return (
    <form aria-labelledby={`${id}-title`} className="space-y-2 rounded-lg border p-3" onSubmit={(e) => {
      e.preventDefault();
      rewrite.mutate({ documentId: doc.id, notes: notes.trim() }, { onSuccess: () => { setNotes(""); setAsked(false); } });
    }}>
      <h4 id={`${id}-title`} className="text-sm font-semibold">{t("review.rewrite_title")}</h4>
      <p id={`${id}-hint`} className="text-sm text-muted-foreground">
        {t(corrections > 0 ? "review.rewrite_hint_corrections" : "review.rewrite_hint")}
      </p>
      <Label htmlFor={id}>{t("review.rewrite_notes")}</Label>
      <Textarea id={id} lang="en" rows={3} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)}
        aria-describedby={`${id}-hint`} />
      {rewrite.error ? <ErrorNotice message={error(isApiError(rewrite.error) ? rewrite.error.code : "INTERNAL")} /> : null}
      <div className="flex gap-2">
        <Button type="submit" size="sm" className="gap-2" disabled={rewrite.isPending || (corrections === 0 && !notes.trim())}>
          <Renew aria-hidden />{t("review.rewrite")}<span className="sr-only">: {name}</span>
        </Button>
        {corrections === 0 ? <Button type="button" size="sm" variant="outline" onClick={() => setAsked(false)}>{t("action.cancel")}</Button> : null}
      </div>
    </form>
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
  const [busy, setBusy] = useState<"" | "pdf" | "html" | "docx">("");
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

  async function download(kind: "pdf" | "html" | "docx") {
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
            <Button variant="outline" className="gap-2" onClick={() => download("docx")} disabled={busy !== ""}
              aria-describedby={`word-hint-${doc.id}`}>
              <Download aria-hidden />{busy === "docx" ? t("documents.word_making") : t("documents.download_word")}
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => download("html")} disabled={busy !== ""}>
              <Download aria-hidden />{t("documents.download_html")}
            </Button>
            <p id={`word-hint-${doc.id}`} className="basis-full text-sm text-muted-foreground">{t("documents.word_hint")}</p>
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
