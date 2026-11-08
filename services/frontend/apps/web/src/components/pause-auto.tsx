"use client";

/** Pause Auto: the one switch that stops all automation (plan principle 2). A switch, as the HIG has it. */
import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { cn } from "@apply/ui";
import { toast } from "sonner";

import { useAutoSettings, useUpdateAutoSettings } from "@/lib/auto";

export function PauseAutoSwitch() {
  const { t, error } = useI18n();
  const settings = useAutoSettings();
  const update = useUpdateAutoSettings();
  const paused = settings.data?.auto_paused ?? false;
  return (
    <button type="button" role="switch" aria-checked={paused} disabled={!settings.data || update.isPending}
      onClick={() => update.mutate({ auto_paused: !paused }, {
        onSuccess: (s) => toast(t(s.auto_paused ? "auto.paused_toast" : "auto.resumed_toast")),
        onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")),
      })}
      className="inline-flex min-h-11 items-center gap-3 rounded-md px-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-ring">
      <span aria-hidden className={cn("relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border-2 transition-colors",
        paused ? "border-primary bg-primary" : "border-input bg-muted")}>
        {/* Thumb and track are tested token pairs (CONTRAST.md): muted-foreground on muted, primary-foreground on primary. */}
        <span className={cn("inline-block size-4 rounded-full shadow transition-transform motion-reduce:transition-none",
          paused ? "translate-x-5 bg-primary-foreground" : "translate-x-0.5 bg-muted-foreground")} />
      </span>
      {t("auto.pause")}
    </button>
  );
}

export function PausedBanner() {
  const { t } = useI18n();
  const settings = useAutoSettings();
  if (!settings.data?.auto_paused) return null;
  return <p role="status" className="rounded-lg border border-primary bg-primary/10 p-3 text-sm">{t("auto.paused_banner")}</p>;
}
