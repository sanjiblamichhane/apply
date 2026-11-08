/**
 * What the side panel shows, decided from what it knows: the connection, the page in the tab, what apply
 * has for it, and whether a submission was just recorded. Pure, so every case is tested.
 */
import type { FillSheet, Lookup, Opportunity } from "@apply/api";
import type { FillResult } from "@apply/ats-adapters";

import type { PageInfo, Recorded } from "../messages";

export type View =
  | { kind: "loading" }
  | { kind: "connect" }
  | { kind: "unsupported" }
  | { kind: "sign_in" }
  | { kind: "job_page" }
  | { kind: "reload" }
  | { kind: "waiting" }
  | { kind: "untracked"; page: PageInfo; opportunity: Opportunity | null }
  | { kind: "ready"; page: PageInfo; sheet: FillSheet; result: FillResult | null }
  | { kind: "recorded"; recorded: Recorded };

export interface Known {
  connected: boolean;
  /** undefined: not asked yet; null: no content script answered (not a board, or loaded before the extension). */
  page?: PageInfo | null;
  onBoardHost?: boolean;
  recorded?: Recorded | null;
  lookup?: Lookup | null;
  sheet?: FillSheet | null;
  result?: FillResult | null;
  /** The form the result is for (PageInfo.formKey): a new step has none yet. */
  resultFor?: string;
}

const RECENT = 60 * 60 * 1000;

export function decide(k: Known, now: number = Date.now()): View {
  if (!k.connected) return { kind: "connect" };
  if (k.page === undefined) return { kind: "loading" };
  if (k.page === null) return { kind: k.onBoardHost ? "reload" : "unsupported" };
  const page = k.page;
  if (k.recorded && now - k.recorded.at < RECENT && (page.isConfirmation || k.recorded.error || k.recorded.undone)) {
    return { kind: "recorded", recorded: k.recorded };
  }
  // On a board apply knows: what to do to get to its form (sign in; press Apply on the job).
  if (page.signIn && page.board !== "other") return { kind: "sign_in" };
  if (!page.isForm) {
    return page.board === "other" || page.isConfirmation ? { kind: "unsupported" } : { kind: "job_page" };
  }
  if (!page.ready) return { kind: "waiting" };
  if (k.lookup === undefined) return { kind: "loading" };
  if (k.lookup === null || k.lookup.application === null) {
    return { kind: "untracked", page, opportunity: k.lookup?.opportunity ?? null };
  }
  if (!k.sheet) return { kind: "loading" };
  const result = k.result && (k.resultFor === undefined || k.resultFor === page.formKey) ? k.result : null;
  return { kind: "ready", page, sheet: k.sheet, result };
}

/** The summary kept with a submission: counts and labels, never the values. */
export function filledSummary(result: FillResult): { fields: number; files: string[]; left_blank: string[] } {
  return { fields: result.filled, files: result.attached, left_blank: result.leftBlank.map((b) => b.label).slice(0, 100) };
}

export function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
}
