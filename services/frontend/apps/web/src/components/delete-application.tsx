"use client";

import { type Application, call, isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { Button } from "@apply/ui";
import { Trash } from "@apply/ui/icons";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { keys } from "@/lib/queries";

const UNDO_MS = 6000;

/**
 * Delete, forgiving rather than asking first (HIG): the card goes and the detail closes at once, with Undo for a
 * few seconds; only then is the application deleted. Leaving the page meanwhile deletes it too (it was asked for).
 */
export function DeleteApplication({ application, title }: { application: Application; title: string }) {
  const { t, error } = useI18n();
  const client = useQueryClient();
  const router = useRouter();

  function remove() {
    const before = client.getQueriesData<Application[]>({ queryKey: keys.applications });
    client.setQueriesData<Application[]>({ queryKey: keys.applications },
      (list) => list?.filter((a) => a.id !== application.id));
    let settled = false;
    const path = `/api/v1/applications/${application.id}`;
    const onLeave = () => {
      if (!settled) void fetch(path, { method: "DELETE", credentials: "same-origin", keepalive: true });
    };
    window.addEventListener("pagehide", onLeave);
    const commit = async () => {
      if (settled) return;
      settled = true;
      window.removeEventListener("pagehide", onLeave);
      try {
        await call(api.DELETE("/api/v1/applications/{application_id}", { params: { path: { application_id: application.id } } }));
        client.removeQueries({ queryKey: keys.application(application.id) });
      } catch (e) {
        for (const [key, data] of before) client.setQueryData(key, data);
        toast.error(error(isApiError(e) ? e.code : "INTERNAL"));
      } finally {
        void client.invalidateQueries({ queryKey: keys.applications });
      }
    };
    router.push("/applications");
    toast(t("application.deleted", { title }), {
      duration: UNDO_MS,
      action: {
        label: t("action.undo"),
        onClick: () => {
          settled = true;
          window.removeEventListener("pagehide", onLeave);
          for (const [key, data] of before) client.setQueryData(key, data);
        },
      },
      onAutoClose: () => void commit(),
      onDismiss: () => void commit(),
    });
  }

  return (
    <Button variant="ghost" className="gap-2" onClick={remove} title={t("application.delete_hint")}>
      <Trash aria-hidden />{t("action.delete")}<span className="sr-only">: {title}</span>
    </Button>
  );
}
