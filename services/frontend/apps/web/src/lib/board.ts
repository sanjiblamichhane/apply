import type { Application, Stage } from "@apply/api";

export type View = "board" | "list";

/** ?view= and ?q= from the URL: the board's state is in the address, so back, reload and sharing work. */
export function readListState(params: URLSearchParams): { view: View; query: string } {
  return { view: params.get("view") === "list" ? "list" : "board", query: (params.get("q") ?? "").trim() };
}

export function writeListState(params: URLSearchParams, changes: { view?: View; query?: string }): string {
  const next = new URLSearchParams(params);
  if (changes.view !== undefined) {
    if (changes.view === "board") next.delete("view");
    else next.set("view", changes.view);
  }
  if (changes.query !== undefined) {
    if (changes.query.trim()) next.set("q", changes.query.trim());
    else next.delete("q");
  }
  const text = next.toString();
  return text ? `?${text}` : "";
}

/** The pipeline's columns, in order, without archived stages. */
export function boardStages(stages: Stage[]): Stage[] {
  return stages.filter((s) => !s.is_archived).sort((a, b) => a.position - b.position);
}

/** Applications whose title or company contains every word of the query (any case, any accents). */
export function filterApplications(items: Application[], query: string): Application[] {
  const words = normalise(query).split(/\s+/).filter(Boolean);
  if (words.length === 0) return items;
  return items.filter((app) => {
    const haystack = normalise(`${app.opportunity.title} ${app.opportunity.issuer_name}`);
    return words.every((word) => haystack.includes(word));
  });
}

function normalise(text: string): string {
  return text.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase();
}

export type DocumentBadge = "ready" | "pending" | "failed" | "none";

/** For a card: each generatable document's state, from the newest of that type. */
export function documentBadges(app: Application, types: string[]): Record<string, DocumentBadge> {
  const out: Record<string, DocumentBadge> = {};
  for (const type of types) {
    const newest = app.current_documents.filter((d) => d.document_type === type).sort((a, b) => (a.id < b.id ? 1 : -1))[0];
    out[type] = newest ? newest.status : "none";
  }
  return out;
}
