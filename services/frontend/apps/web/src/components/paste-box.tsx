"use client";

import { isApiError } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { Button, Label, Textarea } from "@apply/ui";
import { Add } from "@apply/ui/icons";
import { useRouter } from "next/navigation";
import { type FormEvent, type KeyboardEvent, useId, useState } from "react";
import { toast } from "sonner";

import { useCurrentPack } from "@/lib/pack-choice";
import { usePaste } from "@/lib/queries";

/** One link and nothing else is a link; anything else is the posting's text. */
export function asPaste(value: string): { url: string } | { text: string } | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  return /^https?:\/\/\S+$/i.test(trimmed) ? { url: trimmed } : { text: trimmed };
}

/** Paste a job: a link or its text. On success, open the application. */
export function PasteBox() {
  const { t, error: errorText } = useI18n();
  const [currentPack] = useCurrentPack();
  const router = useRouter();
  const paste = usePaste();
  const [value, setValue] = useState("");
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const input = asPaste(value);
    if (!input || paste.isPending) return;
    try {
      const { application, known } = await paste.mutateAsync(input);
      setValue("");
      toast(known ? t("applications.paste.already") : t(forPack("applications.paste.added", currentPack)));
      router.push(`/applications/${application.id}`);
    } catch {
      // Shown under the field, from paste.error.
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Return adds a line (postings are long); ⌘/Ctrl+Return adds the job, as in a chat or mail app.
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) void submit();
  }

  const failure = paste.error ? errorText(isApiError(paste.error) ? paste.error.code : "INTERNAL") : null;

  return (
    <form onSubmit={submit} className="space-y-2 rounded-xl border bg-card p-4">
      <Label htmlFor={id} className="text-base font-semibold">{t(forPack("applications.paste.label", currentPack))}</Label>
      <p id={hintId} className="text-sm text-muted-foreground">{t(forPack("applications.paste.hint", currentPack))}</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
        <Textarea id={id} rows={2} value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={onKeyDown}
          placeholder={t(forPack("applications.paste.placeholder", currentPack))} className="min-h-11 flex-1 resize-y"
          aria-describedby={failure ? `${hintId} ${errorId}` : hintId} aria-invalid={failure ? true : undefined} />
        <Button type="submit" disabled={!asPaste(value) || paste.isPending} className="gap-2">
          <Add aria-hidden />
          {paste.isPending ? t("applications.paste.adding") : t("applications.paste.submit")}
        </Button>
      </div>
      {failure ? <p id={errorId} role="alert" className="text-sm text-destructive">{failure}</p> : null}
    </form>
  );
}
