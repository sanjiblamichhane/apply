"use client";

import { type Answer, ApiError, call, type Document, isApiError } from "@apply/api";
import type { Locale } from "@apply/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import { useCurrentPack } from "./pack-choice";
import { keys } from "./queries";

const doc = (applicationId: string, documentId: string) => ({ application_id: applicationId, document_id: documentId });

function useRefresh(applicationId: string) {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: keys.documents(applicationId) });
    void client.invalidateQueries({ queryKey: ["kit", applicationId] });
  };
}

export function useEditDocument(applicationId: string) {
  const refresh = useRefresh(applicationId);
  return useMutation({
    mutationFn: ({ documentId, content }: { documentId: string; content: string }) =>
      call(api.PUT("/api/v1/applications/{application_id}/documents/{document_id}/content",
        { params: { path: doc(applicationId, documentId) }, body: { content_markdown: content } })),
    onSuccess: refresh,
  });
}

export function useResolveWarning(applicationId: string) {
  const client = useQueryClient();
  const refresh = useRefresh(applicationId);
  return useMutation({
    mutationFn: ({ documentId, warningId, resolution }: { documentId: string; warningId: string; resolution: "kept" | "open" }) =>
      call(api.POST("/api/v1/applications/{application_id}/documents/{document_id}/warnings/{warning_id}",
        { params: { path: { ...doc(applicationId, documentId), warning_id: warningId } }, body: { resolution } })),
    onSuccess: (updated: Document) => {
      client.setQueryData<Document[]>(keys.documents(applicationId), (list) => list?.map((d) => (d.id === updated.id ? updated : d)));
      refresh();
    },
  });
}

export function useMarkReviewed(applicationId: string) {
  const client = useQueryClient();
  const refresh = useRefresh(applicationId);
  return useMutation({
    mutationFn: ({ documentId, reviewed }: { documentId: string; reviewed: boolean }) =>
      call(api.POST("/api/v1/applications/{application_id}/documents/{document_id}/review",
        { params: { path: doc(applicationId, documentId) }, body: { reviewed } })),
    onSuccess: (updated: Document) => {
      client.setQueryData<Document[]>(keys.documents(applicationId), (list) => list?.map((d) => (d.id === updated.id ? updated : d)));
      refresh();
    },
  });
}

export function useCheckAgain(applicationId: string) {
  const refresh = useRefresh(applicationId);
  return useMutation({
    mutationFn: (documentId: string) => call(api.POST("/api/v1/applications/{application_id}/documents/{document_id}/check",
      { params: { path: doc(applicationId, documentId) } })),
    onSuccess: refresh,
  });
}

/** The version as a file (its page, its PDF), waiting while the worker makes it (RENDER_PENDING meanwhile). */
export async function fetchFile(applicationId: string, documentId: string, kind: "pdf" | "html", tries = 60): Promise<Blob> {
  const url = `/api/v1/applications/${applicationId}/documents/${documentId}/${kind}`;
  for (let i = 0; i < tries; i++) {
    const response = await fetch(url, { credentials: "same-origin" });
    if (response.ok) return response.blob();
    const problem = await response.json().catch(() => null);
    if (response.status !== 409 || problem?.code !== "RENDER_PENDING") {
      throw new ApiError(problem?.code ?? "INTERNAL", response.status, problem);
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new ApiError("RENDER_PENDING", 409, null);
}

export const fetchPdf = (applicationId: string, documentId: string) => fetchFile(applicationId, documentId, "pdf");

/** Hands a file to the browser to save. */
export function save(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  Object.assign(window.document.createElement("a"), { href: url, download: filename }).click();
  URL.revokeObjectURL(url);
}

export function useKit(applicationId: string) {
  return useQuery({
    queryKey: ["kit", applicationId],
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}/kit", { params: { path: { application_id: applicationId } } })),
  });
}

export function useSubmit(applicationId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (note: string) => call(api.POST("/api/v1/applications/{application_id}/submissions",
      { params: { path: { application_id: applicationId } }, body: { note } })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["kit", applicationId] });
      void client.invalidateQueries({ queryKey: keys.application(applicationId) });
      void client.invalidateQueries({ queryKey: keys.history(applicationId) });
      void client.invalidateQueries({ queryKey: keys.applications });
    },
  });
}

export function useUndoSubmission(applicationId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (submissionId: string) => call(api.POST("/api/v1/submissions/{submission_id}/undo",
      { params: { path: { submission_id: submissionId } } })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["kit", applicationId] });
      void client.invalidateQueries({ queryKey: keys.application(applicationId) });
      void client.invalidateQueries({ queryKey: keys.history(applicationId) });
    },
  });
}

export function useAnswers() {
  const [pack] = useCurrentPack();
  return useQuery({
    queryKey: ["answers", pack],
    queryFn: () => call(api.GET("/api/v1/answers", { params: { query: { pack } } })).then((r) => r.items),
  });
}

export function useAddDefaultAnswers() {
  const client = useQueryClient();
  const [pack] = useCurrentPack();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/answers/defaults", { params: { query: { pack } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["answers"] }),
  });
}

export function useUpdateAnswer() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) =>
      call(api.PATCH("/api/v1/answers/{answer_id}", { params: { path: { answer_id: id } }, body: { answer } })),
    onSuccess: (updated: Answer) => {
      client.setQueriesData<Answer[]>({ queryKey: ["answers"] }, (list) => list?.map((a) => (a.id === updated.id ? updated : a)));
      void client.invalidateQueries({ queryKey: ["kit"] });
    },
  });
}

export function useCreateAnswer() {
  const client = useQueryClient();
  const [pack] = useCurrentPack();
  return useMutation({
    mutationFn: (body: { key: string; question: { en: string; ne?: string }; answer: string }) =>
      call(api.POST("/api/v1/answers", { body: { pack, answer_type: "text", is_sensitive: false, ...body } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["answers"] }),
  });
}

export function useDeleteAnswer() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/answers/{answer_id}", { params: { path: { answer_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["answers"] }),
  });
}

/** An answer as the kit shows it: a choice's label, yes/no in words, the text otherwise. */
export function answerText(answer: Answer, words: { yes: string; no: string }, locale: Locale): string {
  if (answer.answer_type === "yes_no") return answer.answer === "yes" ? words.yes : answer.answer === "no" ? words.no : "";
  if (answer.answer_type === "choice") {
    const choice = answer.choices.find((c) => c.value === answer.answer);
    return choice ? choice.label[locale] || choice.label.en : answer.answer;
  }
  return answer.answer;
}

export { isApiError };
