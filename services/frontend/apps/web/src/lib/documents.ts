import type { Document } from "@apply/api";

export type DocumentState =
  | { kind: "none" }
  | { kind: "pending"; pending: Document; current: Document | null }
  | { kind: "failed"; failed: Document; current: Document | null }
  | { kind: "ready"; current: Document };

/**
 * What a document panel shows for one type. The version in use stays shown while a new one is written, and a
 * failure is shown above it; the newest attempt (pending or failed) wins over older failures.
 */
export function documentState(documents: Document[], type: string): DocumentState {
  const ofType = documents.filter((d) => d.document_type === type).sort((a, b) => (a.id < b.id ? 1 : -1));
  const current = ofType.find((d) => d.is_active && d.status === "ready") ?? null;
  const newest = ofType[0];
  if (!newest) return { kind: "none" };
  if (newest.status === "pending") return { kind: "pending", pending: newest, current };
  if (newest.status === "failed") return { kind: "failed", failed: newest, current };
  return current ? { kind: "ready", current } : { kind: "ready", current: newest };
}

/** Finished versions of a type, newest first. */
export function versions(documents: Document[], type: string): Document[] {
  return documents.filter((d) => d.document_type === type && d.status === "ready" && d.version > 0)
    .sort((a, b) => b.version - a.version);
}

export function anyPending(documents: Document[] | undefined): boolean {
  // Being written, or written and still being checked: either way, look again soon.
  return Boolean(documents?.some((d) => d.status === "pending" || (d.status === "ready" && d.claims_status === "pending")));
}

/** Warnings not yet decided on. */
export function openWarnings(document: Document): number {
  return document.claim_warnings.filter((w) => !w.resolved).length;
}

/** How many "[CONFIRM: …]" markers the model left for the person to check. */
export function confirmMarkers(markdown: string): number {
  return (markdown.match(/\[CONFIRM:[^\]]*\]/g) ?? []).length;
}

export function downloadName(title: string, type: string, version: number): string {
  const slug = [title, type].filter(Boolean).join(" ").toLowerCase().normalize("NFKD").replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "").slice(0, 80);
  return `${slug || "document"}-v${version}.md`;
}
