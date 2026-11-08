"use client";

import {
  type Application,
  call,
  type ChooseModel,
  type Document,
  isApiError,
  type Me,
  type NewProfile,
  type Opportunity,
  type OpportunityChanges,
  type ProfileChanges,
} from "@apply/api";
import type { Locale } from "@apply/i18n";
import { backoffInterval } from "@apply/kit";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";

import { api } from "./api";
import { anyPending } from "./documents";
import { DEFAULT_PACK, useCurrentPack } from "./pack-choice";

export const keys = {
  me: ["me"] as const,
  pack: (key: string) => ["pack", key] as const,
  applications: ["applications"] as const, // every pack's: the prefix of each pack's list
  applicationsOf: (pack: string) => ["applications", pack] as const,
  application: (id: string) => ["application", id] as const,
  history: (id: string) => ["application", id, "history"] as const,
  documents: (id: string) => ["application", id, "documents"] as const,
  opportunity: (id: string) => ["opportunity", id] as const,
  profiles: ["profiles"] as const,
  profilesOf: (pack: string) => ["profiles", pack] as const,
  profile: (id: string) => ["profile", id] as const,
  model: ["model"] as const,
  models: ["models"] as const,
};

/** Polling while something is pending: often at first, then less often, from when it started pending. */
function usePendingInterval() {
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

// ── account ──────────────────────────────────────────────────────────────────

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: () => call(api.GET("/api/v1/auth/me")), staleTime: 60_000 });
}

export function useSignIn() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => call(api.POST("/api/v1/auth/sign-in", { body })),
    onSuccess: (me: Me) => {
      client.clear();
      client.setQueryData(keys.me, me);
    },
  });
}

/** Whether "Create your account" is open (a fresh install, with web setup on). */
export function useSetup() {
  return useQuery({ queryKey: ["setup"], queryFn: () => call(api.GET("/api/v1/auth/setup")), staleTime: 0 });
}

/** Ask for a reset link: the answer is the same whether or not there's such an account. */
export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => call(api.POST("/api/v1/auth/forgot-password", { body: { email } })),
  });
}

/** The account a reset link is for, or RESET_LINK_INVALID. */
export function useResetFor(token: string | null) {
  return useQuery({
    queryKey: ["reset", token],
    queryFn: () => call(api.POST("/api/v1/auth/reset-password/check", { body: { token: token! } })),
    enabled: Boolean(token),
    retry: false,
    staleTime: Infinity,
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (body: { token: string; password: string }) =>
      call(api.POST("/api/v1/auth/reset-password", { body })),
  });
}

export function useRegister() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string; locale: Locale; demo?: boolean }) =>
      call(api.POST("/api/v1/auth/register", { body })),
    onSuccess: (me: Me) => {
      client.clear();
      client.setQueryData(keys.me, me);
    },
  });
}

export function useSignOut() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/auth/sign-out")),
    onSettled: () => client.clear(),
  });
}

export function useUpdateMe() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { locale: Locale }) => call(api.PATCH("/api/v1/auth/me", { body })),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useModelStatus() {
  return useQuery({ queryKey: keys.model, queryFn: () => call(api.GET("/api/v1/system/model")), staleTime: 0 });
}

/** The model servers on this computer and their models, and the model in use. Looked for on demand, not polled. */
export function useModels() {
  return useQuery({
    queryKey: keys.models,
    queryFn: () => call(api.GET("/api/v1/system/models")),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

/** Test a model and, if it answers, use it from the next call on. */
export function useChooseModel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ChooseModel) => call(api.PUT("/api/v1/system/model", { body })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: keys.models });
      void client.invalidateQueries({ queryKey: keys.model });
    },
  });
}

/** Back to the model in the settings (.env). */
export function useResetModel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.DELETE("/api/v1/system/model")),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: keys.models });
      void client.invalidateQueries({ queryKey: keys.model });
    },
  });
}

// ── packs ────────────────────────────────────────────────────────────────────

export function usePack(key = DEFAULT_PACK) {
  return useQuery({
    queryKey: keys.pack(key),
    queryFn: () => call(api.GET("/api/v1/packs/{key}", { params: { path: { key } } })),
    staleTime: 10 * 60_000,
  });
}

/** Every pack the API has, for the switcher. */
export function usePacks() {
  return useQuery({
    queryKey: ["packs"],
    queryFn: () => call(api.GET("/api/v1/packs")).then((r) => r.items),
    staleTime: 10 * 60_000,
  });
}

/** The pack the screens are working in, as the API describes it. */
export function useCurrentPackInfo() {
  const [key] = useCurrentPack();
  return usePack(key);
}

// ── applications ─────────────────────────────────────────────────────────────

/** Every application in the current pack (the board needs them all), page by page. */
export function useApplications() {
  const interval = usePendingInterval();
  const [pack] = useCurrentPack();
  return useQuery({
    queryKey: keys.applicationsOf(pack),
    queryFn: async () => {
      const items: Application[] = [];
      let after: string | undefined;
      for (let page = 0; page < 50; page++) {
        const result = await call(api.GET("/api/v1/applications", { params: { query: { pack, limit: 200, after } } }));
        items.push(...result.items);
        if (!result.next_cursor) break;
        after = result.next_cursor;
      }
      return items;
    },
    refetchInterval: (query) => interval(Boolean(query.state.data?.some((a) =>
      a.opportunity.extraction.status === "pending" || a.current_documents.some((d) => d.status === "pending")))),
  });
}

export function useApplication(id: string) {
  return useQuery({
    queryKey: keys.application(id),
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}", { params: { path: { application_id: id } } })),
  });
}

export function useHistory(id: string) {
  return useQuery({
    queryKey: keys.history(id),
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}/history",
      { params: { path: { application_id: id } } })).then((r) => r.items),
  });
}

/** Paste a link or text: the opportunity, then its application (or the one already tracking it). */
export function usePaste() {
  const client = useQueryClient();
  const [pack] = useCurrentPack();
  return useMutation({
    mutationFn: async (input: { url?: string; text?: string }): Promise<{ application: Application; known: boolean }> => {
      const opportunity = await call(api.POST("/api/v1/opportunities", { body: { pack, ...input } }));
      try {
        const application = await call(api.POST("/api/v1/applications", { body: { opportunity_id: opportunity.id } }));
        return { application, known: false };
      } catch (error) {
        const existing = isApiError(error, "APPLICATION_EXISTS") ? error.problem?.application_id : null;
        if (!existing) throw error;
        const application = await call(api.GET("/api/v1/applications/{application_id}",
          { params: { path: { application_id: existing } } }));
        return { application, known: true };
      }
    },
    onSuccess: () => client.invalidateQueries({ queryKey: keys.applications }),
  });
}

export function useMove() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, stage_code, note }: { id: string; stage_code: string; note?: string }) =>
      call(api.POST("/api/v1/applications/{application_id}/stage",
        { params: { path: { application_id: id } }, body: { stage_code, note: note ?? "" } })),
    onSuccess: (app) => {
      client.setQueryData(keys.application(app.id), app);
      client.setQueriesData<Application[]>({ queryKey: keys.applications },
        (list) => list?.map((a) => (a.id === app.id ? app : a)));
      void client.invalidateQueries({ queryKey: keys.history(app.id) });
    },
  });
}

export function useUpdateApplication(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { notes?: string; profile_id?: string | null }) =>
      call(api.PATCH("/api/v1/applications/{application_id}", { params: { path: { application_id: id } }, body })),
    onSuccess: (app) => {
      client.setQueryData(keys.application(id), app);
      void client.invalidateQueries({ queryKey: keys.applications });
    },
  });
}

// ── opportunities ────────────────────────────────────────────────────────────

export function useOpportunity(id: string | undefined) {
  const interval = usePendingInterval();
  return useQuery({
    queryKey: keys.opportunity(id ?? ""),
    enabled: Boolean(id),
    queryFn: () => call(api.GET("/api/v1/opportunities/{opportunity_id}", { params: { path: { opportunity_id: id! } } })),
    refetchInterval: (query) => interval(query.state.data?.extraction.status === "pending"),
  });
}

export function useUpdateOpportunity(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: OpportunityChanges) =>
      call(api.PATCH("/api/v1/opportunities/{opportunity_id}", { params: { path: { opportunity_id: id } }, body })),
    onSuccess: (opp: Opportunity) => {
      client.setQueryData(keys.opportunity(id), opp);
      void client.invalidateQueries({ queryKey: keys.applications });
      void client.invalidateQueries({ queryKey: ["application"] });
    },
  });
}

export function useExtractAgain(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/opportunities/{opportunity_id}/extract",
      { params: { path: { opportunity_id: id } } })),
    onSuccess: (opp) => client.setQueryData(keys.opportunity(id), opp),
  });
}

// ── documents ────────────────────────────────────────────────────────────────

export function useDocuments(applicationId: string) {
  const interval = usePendingInterval();
  return useQuery({
    queryKey: keys.documents(applicationId),
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}/documents",
      { params: { path: { application_id: applicationId } } })).then((r) => r.items),
    refetchInterval: (query) => interval(anyPending(query.state.data)),
  });
}

export function useWriteDocument(applicationId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (document_type: string) => call(api.POST("/api/v1/applications/{application_id}/documents",
      { params: { path: { application_id: applicationId } }, body: { document_type } })),
    onSuccess: (doc: Document) => {
      client.setQueryData<Document[]>(keys.documents(applicationId),
        (list) => [doc, ...(list ?? []).filter((d) => d.id !== doc.id)]);
      void client.invalidateQueries({ queryKey: keys.documents(applicationId) });
    },
  });
}

// ── profiles ─────────────────────────────────────────────────────────────────

/** The current pack's profiles (or ``pack``'s, for an application in another). */
export function useProfiles(pack?: string) {
  const [current] = useCurrentPack();
  const key = pack ?? current;
  return useQuery({
    queryKey: keys.profilesOf(key),
    queryFn: () => call(api.GET("/api/v1/profiles", { params: { query: { pack: key, limit: 200 } } }))
      .then((r) => r.items),
  });
}

export function useProfile(id: string) {
  const interval = usePendingInterval();
  return useQuery({
    queryKey: keys.profile(id),
    queryFn: () => call(api.GET("/api/v1/profiles/{profile_id}", { params: { path: { profile_id: id } } })),
    // While the model reads the document it was made from.
    refetchInterval: (query) => interval(query.state.data?.reading?.status === "pending"),
  });
}

/** A profile from a document (a resume): made at once, then read by the model (useProfile polls it). */
export function useImportProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ file, pack }: { file: File; pack: string }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("pack", pack);
      return call(api.POST("/api/v1/profiles/import", {
        body: { file: "", pack },
        bodySerializer: () => form,
      }));
    },
    onSuccess: (profile) => {
      client.setQueryData(keys.profile(profile.id), profile);
      void client.invalidateQueries({ queryKey: keys.profiles });
    },
  });
}

export function useDuplicateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      call(api.POST("/api/v1/profiles/{profile_id}/duplicate", { params: { path: { profile_id: id } }, body: { name } })),
    onSuccess: (profile) => {
      client.setQueryData(keys.profile(profile.id), profile);
      void client.invalidateQueries({ queryKey: keys.profiles });
    },
  });
}

export function useReadProfileAgain(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/profiles/{profile_id}/read", { params: { path: { profile_id: id } } })),
    onSuccess: (profile) => client.setQueryData(keys.profile(id), profile),
  });
}

export function useCreateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: NewProfile) => call(api.POST("/api/v1/profiles", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.profiles }),
  });
}

export function useUpdateProfile(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileChanges) =>
      call(api.PATCH("/api/v1/profiles/{profile_id}", { params: { path: { profile_id: id } }, body })),
    onSuccess: (profile) => {
      client.setQueryData(keys.profile(id), profile);
      void client.invalidateQueries({ queryKey: keys.profiles });
    },
  });
}

export function useDeleteProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/profiles/{profile_id}", { params: { path: { profile_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.profiles }),
  });
}
