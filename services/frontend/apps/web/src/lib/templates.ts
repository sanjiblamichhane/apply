"use client";

import { call, type Template, type TemplateCheck, type TemplateKind } from "@apply/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

const key = (kind: TemplateKind) => ["template", kind] as const;
const path = (kind: TemplateKind) => ({ params: { path: { kind } } });

/** The template documents of this kind are made in (the person's own, or the default), with a sample in it. */
export function useTemplate(kind: TemplateKind) {
  return useQuery({ queryKey: key(kind), queryFn: () => call(api.GET("/api/v1/templates/{kind}", path(kind))) });
}

export const defaultTemplate = (kind: TemplateKind): Promise<Template> =>
  call(api.GET("/api/v1/templates/{kind}/default", path(kind)));

export const checkTemplate = (kind: TemplateKind, html: string): Promise<TemplateCheck> =>
  call(api.POST("/api/v1/templates/{kind}/check", { ...path(kind), body: { html } }));

/** Keep a template (it's checked again), or go back to the default; documents are made again in it when asked for. */
export function useSaveTemplate(kind: TemplateKind) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ html, filename }: { html: string; filename: string }) =>
      call(api.PUT("/api/v1/templates/{kind}", { ...path(kind), body: { html, filename } })),
    onSuccess: (saved) => client.setQueryData(key(kind), saved),
  });
}

export function useResetTemplate(kind: TemplateKind) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.DELETE("/api/v1/templates/{kind}", path(kind))),
    onSuccess: () => client.invalidateQueries({ queryKey: key(kind) }),
  });
}
