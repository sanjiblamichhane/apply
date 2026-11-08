"use client";

import { type AutoRun, type AutoSettingsChanges, call } from "@apply/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

export type RunGroup = "waiting" | "ready" | "needs_you" | "done";
// Runs from before apply stopped sending, where Submit was pressed without a clear answer: never started again.
export const MAY_HAVE_GONE = new Set(["AUTO_SEND_UNKNOWN", "AUTO_NO_CONFIRMATION"]);

export const autoKeys = {
  settings: ["auto", "settings"] as const,
  counts: ["auto", "counts"] as const,
  runs: (group: RunGroup) => ["auto", "runs", group] as const,
};

/** What can be done with a run now. */
export function actionsFor(run: Pick<AutoRun, "status" | "reason" | "application_id">) {
  return {
    stop: ["starting", "writing", "ready"].includes(run.status),
    review: !!run.application_id,
    retry: (run.status === "needs_you" || run.status === "stopped") && !MAY_HAVE_GONE.has(run.reason ?? ""),
    dismiss: run.status === "needs_you" || run.status === "stopped",
  };
}

export function useAutoSettings() {
  return useQuery({ queryKey: autoKeys.settings, queryFn: () => call(api.GET("/api/v1/auto/settings")) });
}

export function useUpdateAutoSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: AutoSettingsChanges) => call(api.PATCH("/api/v1/auto/settings", { body })),
    onSuccess: (saved) => {
      client.setQueryData(autoKeys.settings, saved);
      void client.invalidateQueries({ queryKey: ["auto"] });
    },
  });
}

export function useAutoCounts() {
  return useQuery({
    queryKey: autoKeys.counts,
    queryFn: () => call(api.GET("/api/v1/auto/counts")),
    refetchInterval: 15_000,
  });
}

/** Where to apply: the posting's application form on its board (a web address only), or null. */
export function formUrl(run: { opportunity: Pick<AutoRun["opportunity"], "apply_url" | "source_url"> }): string | null {
  const url = run.opportunity.apply_url || run.opportunity.source_url;
  return url && /^https?:\/\//i.test(url) ? url : null;
}

export function useRuns(group: RunGroup) {
  return useQuery({
    queryKey: autoKeys.runs(group),
    queryFn: async () => (await call(api.GET("/api/v1/auto/runs", { params: { query: { group } } }))).items,
    // Runs being prepared move on their own (documents written and checked): look often while any is.
    refetchInterval: (query) => (group === "waiting" ? ((query.state.data ?? []).length ? 3000 : 15_000) : 10_000),
  });
}

type Action = "stop" | "retry" | "dismiss";

export function useRunAction() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: Action }) => {
      const path = { params: { path: { run_id: id } } };
      switch (action) {
        case "stop": return call(api.POST("/api/v1/auto/runs/{run_id}/stop", path));
        case "retry": return call(api.POST("/api/v1/auto/runs/{run_id}/retry", path));
        case "dismiss": return call(api.POST("/api/v1/auto/runs/{run_id}/dismiss", path));
      }
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["auto"] }),
  });
}
