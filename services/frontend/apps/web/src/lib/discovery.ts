"use client";

import { type Briefing, call, type Match, type NewSearch, type NewSource, type Search, type Source } from "@apply/api";
import { backoffInterval } from "@apply/kit";
import { type InfiniteData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";

import { api } from "./api";
import { useCurrentPack } from "./pack-choice";

export type MatchStatus = "new" | "saved" | "dismissed" | "tracked";

// Each list's key starts with its name, then the pack: invalidating by the name refreshes every pack's.
export const discoveryKeys = {
  kinds: (pack: string) => ["source-kinds", pack] as const,
  sources: ["sources"] as const,
  sourcesOf: (pack: string) => ["sources", pack] as const,
  searches: ["searches"] as const,
  searchesOf: (pack: string) => ["searches", pack] as const,
  matches: (pack: string, status: MatchStatus) => ["matches", pack, status] as const,
  briefing: ["briefing"] as const,
};

function usePending() {
  const since = useRef<number | null>(null);
  return (pending: boolean): number | false => {
    if (!pending) {
      since.current = null;
      return false;
    }
    since.current ??= Date.now();
    return backoffInterval(Date.now() - since.current);
  };
}

// ── sources ──────────────────────────────────────────────────────────────────

export function useSourceKinds() {
  const [pack] = useCurrentPack();
  return useQuery({
    queryKey: discoveryKeys.kinds(pack),
    queryFn: () => call(api.GET("/api/v1/source-kinds", { params: { query: { pack } } })).then((r) => r.items),
    staleTime: 10 * 60_000,
  });
}

/** The current pack's sources (or ``of``'s, for a search in another). */
export function useSources(of?: string) {
  const interval = usePending();
  const [current] = useCurrentPack();
  const pack = of ?? current;
  return useQuery({
    queryKey: discoveryKeys.sourcesOf(pack),
    queryFn: () => call(api.GET("/api/v1/sources", { params: { query: { pack } } })).then((r) => r.items),
    // A source just added or asked to check now is fetched in the background: look again until it has.
    refetchInterval: (q) => interval(Boolean(q.state.data?.some((s) => s.enabled && s.last_status === "never"))),
  });
}

/** Which kind of source a pasted address is (a company's job board), and the config it stands for. */
export function useRecogniseSource() {
  const [pack] = useCurrentPack();
  return useMutation({
    mutationFn: (url: string) => call(api.POST("/api/v1/sources/recognise", { body: { pack, url } })),
  });
}

export function useCreateSource() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: NewSource) => call(api.POST("/api/v1/sources", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: discoveryKeys.sources }),
  });
}

export function useUpdateSource() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; enabled?: boolean; name?: string; interval_hours?: number }) =>
      call(api.PATCH("/api/v1/sources/{source_id}", { params: { path: { source_id: id } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: discoveryKeys.sources }),
  });
}

export function useDeleteSource() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/sources/{source_id}", { params: { path: { source_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: discoveryKeys.sources }),
  });
}

export function useFetchSource() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.POST("/api/v1/sources/{source_id}/fetch", { params: { path: { source_id: id } } })),
    onSuccess: (source: Source) => {
      client.setQueriesData<Source[]>({ queryKey: discoveryKeys.sources }, (list) => list?.map((s) => (s.id === source.id ? { ...source, last_status: "never" } : s)));
      void client.invalidateQueries({ queryKey: ["matches"] });
    },
  });
}

// ── searches ─────────────────────────────────────────────────────────────────

export function useSearches() {
  const [pack] = useCurrentPack();
  return useQuery({
    queryKey: discoveryKeys.searchesOf(pack),
    queryFn: () => call(api.GET("/api/v1/searches", { params: { query: { pack } } })).then((r) => r.items),
  });
}

export function useSaveSearch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: NewSearch }): Promise<Search> =>
      id
        ? call(api.PATCH("/api/v1/searches/{search_id}", { params: { path: { search_id: id } }, body }))
        : call(api.POST("/api/v1/searches", { body })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: discoveryKeys.searches });
      void client.invalidateQueries({ queryKey: ["matches"] });
    },
  });
}

export function useDeleteSearch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/searches/{search_id}", { params: { path: { search_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: discoveryKeys.searches }),
  });
}

// ── matches ──────────────────────────────────────────────────────────────────

type MatchPage = { items: Match[]; next_cursor: string | null; counts: { new: number; saved: number; dismissed: number; tracked: number } };

export function useMatches(status: MatchStatus) {
  const interval = usePending();
  const [pack] = useCurrentPack();
  return useInfiniteQuery({
    queryKey: discoveryKeys.matches(pack, status),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }): Promise<MatchPage> =>
      call(api.GET("/api/v1/matches", { params: { query: { pack, status: [status], after: pageParam, limit: 50 } } })),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    refetchInterval: (q) => interval(Boolean(q.state.data?.pages.some((p) => p.items.some((m) => m.score_status === "pending")))),
  });
}

/** Change a match's status at once on screen (and put it back if the server says no). */
export function useMatchStatus() {
  const client = useQueryClient();
  const [pack] = useCurrentPack();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: "new" | "saved" | "dismissed"; from: MatchStatus }) =>
      call(api.PATCH("/api/v1/matches/{match_id}", { params: { path: { match_id: id } }, body: { status } })),
    onMutate: async ({ id, from }) => {
      const key = discoveryKeys.matches(pack, from);
      await client.cancelQueries({ queryKey: key });
      const before = client.getQueryData<InfiniteData<MatchPage>>(key);
      client.setQueryData<InfiniteData<MatchPage>>(key, (data) => data && {
        ...data, pages: data.pages.map((p) => ({ ...p, items: p.items.filter((m) => m.id !== id) })),
      });
      return { before, key };
    },
    onError: (_error, _vars, context) => {
      if (context?.before) client.setQueryData(context.key, context.before);
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["matches"] }),
  });
}

export function useTrack() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.POST("/api/v1/matches/{match_id}/track", { params: { path: { match_id: id } } })),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: ["matches"] });
      void client.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

// ── briefing ─────────────────────────────────────────────────────────────────

export function useBriefing() {
  return useQuery({
    queryKey: discoveryKeys.briefing,
    queryFn: () => call(api.GET("/api/v1/briefings/today")) as Promise<Briefing | null>,
  });
}

export function useBuildBriefing() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/briefings/today")),
    onSuccess: (briefing) => client.setQueryData(discoveryKeys.briefing, briefing),
  });
}

export function useUpdateBriefingTime() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { time_zone?: string; briefing_hour?: number }) => call(api.PATCH("/api/v1/auth/me", { body })),
    onSuccess: (me) => client.setQueryData(["me"], me),
  });
}

/** "Strong", "fair" or "weak" fit, in words beside the number (never colour alone). */
export function fitBand(score: number): "strong" | "fair" | "weak" {
  if (score >= 75) return "strong";
  if (score >= 50) return "fair";
  return "weak";
}

/** A search's rules in one line, for its list. */
export function lines(text: string): string[] {
  return text.split("\n").map((l) => l.trim()).filter(Boolean);
}

/** What a search form offers for a pack: only the options that mean something for it, and Auto where it can send. */
export function searchOptionsFor(pack: { search_options: string[]; auto: boolean } | undefined) {
  const has = (option: string) => Boolean(pack?.search_options.includes(option));
  return { locations: has("locations"), remoteOnly: has("remote_only"), needsSponsorship: has("needs_sponsorship"), auto: Boolean(pack?.auto) };
}
