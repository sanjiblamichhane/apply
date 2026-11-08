/** What the side panel, the content script and the service worker say to each other. */
import type { Board, FillResult, Sheet } from "@apply/ats-adapters";

export interface PageInfo {
  url: string;
  /** "other": a site the person allowed, read by the label rules alone. */
  board: Board;
  isForm: boolean;
  ready: boolean;
  isConfirmation: boolean;
  /** A sign-in (or create-an-account) form is showing: the person signs in first. */
  signIn: boolean;
  /** The form comes in steps, each filled while it's showing (board04). */
  steps: boolean;
  /** The form's shape (its questions): a new step, or a form redrawn, has another. */
  formKey: string;
  postingUrls: string[];
  title: string;
}

export interface FileData {
  document_type: string;
  filename: string;
  base64: string;
}

export type ToContent =
  | { type: "page" }
  | { type: "html" }
  /** What a fill would do, field by field, written nowhere (PreviewRow[]; null where no form is read). */
  | { type: "preview"; sheet: Sheet }
  /** skip: the fields the person unticked in the preview (PreviewRow.key). */
  | { type: "fill"; sheet: Sheet; files: FileData[]; skip?: string[] };

export type FillReply = { ok: true; result: FillResult } | { ok: false; error: string };

export type ToBackground =
  | { type: "confirmed"; url: string }
  /** The copy panel put this on the clipboard: cleared a minute later, if the person asked for that. */
  | { type: "copied"; text: string };

/** Between the service worker and the offscreen page that clears the clipboard. */
export type ClipboardMessage =
  | { type: "clear-later"; text: string; after: number }
  | { type: "clipboard-done" };

/** chrome.storage.local: whether to clear what the copy panel copied, a minute later. */
export const CLEAR_CLIPBOARD = "clearClipboard";
export const CLIPBOARD_PERMISSIONS = ["clipboardWrite", "clipboardRead"] as chrome.runtime.ManifestPermissions[];

/** From the content script, to the panel: the page changed (another address without a load, a step drawn). */
export type PageChanged = { type: "page-changed" };

export type Broadcast = { type: "recorded"; tabId: number };

/** Kept per tab in chrome.storage.session while a filled form waits for the person to submit it. */
export interface PendingFill {
  applicationId: string;
  filled: { fields: number; files: string[]; left_blank: string[] };
  at: number;
}

export interface Recorded {
  applicationId: string;
  submissionId?: string;
  stageCode?: string;
  error?: string;
  undone?: boolean;
  at: number;
}

export const pendingKey = (tabId: number) => `fill:${tabId}`;
export const recordedKey = (tabId: number) => `recorded:${tabId}`;
