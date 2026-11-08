"use client";

/**
 * Profiles made from a document (a resume, a capability statement): "Start from your resume" on New profile, and
 * on a profile's page how the model's reading of it went (reading, filled in: check every field, or couldn't).
 */
import { isApiError, type Profile } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { Button } from "@apply/ui";
import { CheckmarkFilled, DocumentAdd, Download, InProgress, Renew, WarningAlt } from "@apply/ui/icons";
import { useRouter } from "next/navigation";
import { type DragEvent, useId, useRef, useState } from "react";

import { useImportProfile, useReadProfileAgain, useUpdateProfile } from "@/lib/queries";

const ACCEPT = ".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown";

export function ProfileImport({ pack }: { pack: string }) {
  const { t, error } = useI18n();
  const router = useRouter();
  const upload = useImportProfile();
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [over, setOver] = useState(false);

  function send(file: File | undefined) {
    if (!file || upload.isPending) return;
    setName(file.name);
    upload.mutate({ file, pack }, { onSuccess: (profile) => router.push(`/profiles/${profile.id}`) });
  }
  function dropped(event: DragEvent) {
    event.preventDefault();
    setOver(false);
    send(event.dataTransfer.files[0]);
  }

  return (
    <section aria-labelledby={`${id}-title`}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={dropped}
      className={`space-y-3 rounded-xl border bg-card p-4 ${over ? "border-primary ring-2 ring-ring" : ""}`}>
      <h2 id={`${id}-title`} className="text-lg font-semibold">{t(forPack("profiles.import.title", pack))}</h2>
      <p className="text-sm text-muted-foreground">{t(forPack("profiles.import.body", pack))}</p>
      {/* The button opens the file picker; the input itself isn't shown or reached (one control, not two). */}
      <input ref={input} id={`${id}-file`} type="file" accept={ACCEPT} hidden
        onChange={(e) => { send(e.target.files?.[0]); e.target.value = ""; }} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" className="gap-2" disabled={upload.isPending} aria-describedby={`${id}-hint`}
          onClick={() => input.current?.click()}>
          <DocumentAdd aria-hidden />{t("profiles.import.choose")}
        </Button>
        <p id={`${id}-hint`} className="text-sm text-muted-foreground">{t("profiles.import.hint")}</p>
      </div>
      <div aria-live="polite">
        {upload.isPending ? <p role="status" className="text-sm">{t("profiles.import.uploading", { name })}</p> : null}
      </div>
      {upload.error && !upload.isPending ? (
        <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
          <WarningAlt className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{error(isApiError(upload.error) ? upload.error.code : "NETWORK")}</span>
        </p>
      ) : null}
    </section>
  );
}

/** How the reading of the document went, on the profile's page. Nothing for a profile typed in. */
export function ProfileReading({ profile }: { profile: Profile }) {
  const { t, error } = useI18n();
  const update = useUpdateProfile(profile.id);
  const again = useReadProfileAgain(profile.id);
  const { reading, source } = profile;
  if (!reading || !source) return null;
  const name = source.name;
  const download = (
    <a href={`/api/v1/profiles/${profile.id}/source`} download={name}
      className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-primary underline underline-offset-4">
      <Download className="size-4" aria-hidden />{t("profiles.source.download", { name })}
    </a>
  );

  if (reading.status === "pending") {
    return (
      <div role="status" className="space-y-2 rounded-xl border bg-card p-4">
        <p className="flex items-center gap-2 font-medium">
          <InProgress className="size-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden />
          {t("profiles.reading.pending", { name })}
        </p>
        <p className="text-sm text-muted-foreground">{t("profiles.reading.pending_body")}</p>
        <Button variant="outline" disabled={update.isPending} onClick={() => update.mutate({ name: profile.name })}>
          {t("profiles.reading.stop")}
        </Button>
      </div>
    );
  }
  if (reading.status === "failed") {
    return (
      <div role="alert" className="space-y-2 rounded-xl border border-destructive/50 bg-card p-4">
        <p className="flex items-center gap-2 font-medium text-destructive">
          <WarningAlt className="size-4 shrink-0" aria-hidden />{t("profiles.reading.failed", { name })}
        </p>
        {reading.error_code ? <p className="text-sm">{error(reading.error_code)}</p> : null}
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" className="gap-2" disabled={again.isPending} onClick={() => again.mutate()}>
            <Renew aria-hidden />{t("profiles.reading.again")}
          </Button>
          {download}
        </div>
      </div>
    );
  }
  if (reading.status === "ready" && !reading.edited) {
    return (
      <div className="space-y-2 rounded-xl border bg-card p-4">
        <p className="flex items-center gap-2 font-medium">
          <CheckmarkFilled className="size-4 shrink-0 text-success" aria-hidden />{t("profiles.reading.ready", { name })}
        </p>
        <p className="text-sm">{t("profiles.reading.ready_body")}</p>
        {download}
      </div>
    );
  }
  return <p>{download}</p>;
}
