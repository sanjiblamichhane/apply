/**
 * Adapters as data. Most boards need only their key (hosts come from boards.json) and how their addresses
 * look; the form is the one with the most questions on the page, and its questions are read by the label rules
 * (match.ts). A board with its own field names, option buttons or Submit says so here.
 *
 *   export const board06 = defineBoard({ board: "board06", apply: /\/j\/[A-Z0-9]+\/apply/ });
 */
import { BOARD_LIST } from "./boards";
import { pageText, signInShowing } from "./dom";
import type { Adapter, Board, FormField, Source } from "./types";

/** "Thank you for applying", "Your application has been submitted", and the like. */
export const THANKS = /thank(s| you) for (your )?(applying|application|interest)|application (has been |was )?(submitted|received|sent|complete)|we('ve| have) (received|got) your application|successfully (applied|submitted)/i;

const FIELDS = "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=image]):not([type=search]), select, textarea";

/** The form with the most questions on the page (two at least), else null. */
export function biggestForm(doc: Document): HTMLElement | null {
  let best: HTMLElement | null = null;
  let most = 1;
  for (const form of Array.from(doc.querySelectorAll<HTMLElement>("form, [role=form]"))) {
    const count = form.querySelectorAll(FIELDS).length;
    if (count > most) { best = form; most = count; }
  }
  if (best) return best;
  // A form drawn without a <form> (some boards' scripts): the page's main area, if it has questions.
  const main = doc.querySelector<HTMLElement>("main, [role=main]") ?? doc.body;
  return main && main.querySelectorAll(FIELDS).length > 2 ? main : null;
}

export interface BoardSpec {
  board: Board;
  /** The application form's address (its path): where filling is offered. Default: any page with a form. */
  apply?: RegExp;
  /** The form, when the board's is known; default: the biggest form on the page. */
  form?: string;
  /** Containers of one question each (for questions drawn with the board's own controls). */
  questionSelector?: string;
  /** The board's own field names (an input's name or id, or its ``attribute``), before any label rule. */
  names?: Record<string, Source[]>;
  /** Another attribute the board names its controls by (board04: data-automation-id). */
  attribute?: string;
  /** Labels for controls the page leaves unlabelled, by name, id or ``attribute``. */
  labels?: Record<string, string>;
  /** Its form comes in steps, each filled while it's showing (board04). */
  steps?: boolean;
  /** The address of its thank-you page, when it has one; the text on the page is checked either way. */
  thanksPath?: RegExp;
  /** The posting's own address, from the form's (board02's …/apply → …): the URLs apply may know it by. */
  posting?: (url: URL) => string;
  optionButtons?: string;
  /** Its own dropdowns (board04's): read, never opened. */
  dropdowns?: string;
}

/** The posting's address without the form part: …/apply, …/c/new, …/applications/new, and any #fragment. */
export function stripForm(url: URL): string {
  const path = url.pathname.replace(/\/(apply(\/.*)?|c\/new|applications\/new|application)\/?$/i, "") || "/";
  return `${url.protocol}//${url.host}${path}`;
}

export function defineBoard(spec: BoardSpec): Adapter {
  const known = BOARD_LIST.find((b) => b.key === spec.board);
  if (!known) throw new Error(`${spec.board} isn't in boards.json`);
  const root = (doc: Document): ParentNode | null =>
    (spec.form ? doc.querySelector(spec.form) : null) ?? biggestForm(doc);
  const onApply = (url: URL) => !spec.apply || spec.apply.test(url.pathname);
  const keysOf = (el: HTMLElement | undefined): string[] =>
    el ? [el.getAttribute("name") ?? "", el.id, spec.attribute ? el.getAttribute(spec.attribute) ?? "" : ""].filter(Boolean) : [];
  return {
    board: spec.board,
    hosts: known.hosts,
    isForm: (url, doc) => {
      const form = root(doc);
      return onApply(url) && form !== null && !signInShowing(doc) && !THANKS.test(pageText(doc).slice(0, 3000));
    },
    isConfirmation: (url, doc) => !!spec.thanksPath?.test(url.pathname) || THANKS.test(pageText(doc).slice(0, 4000)),
    postingUrls(url) {
      const own = `${url.protocol}//${url.host}${url.pathname}`;
      return [...new Set([spec.posting ? spec.posting(url) : stripForm(url), own])];
    },
    root,
    questionSelector: spec.questionSelector,
    hint: spec.names
      ? (field: FormField) => {
        for (const key of [field.name, field.id, ...keysOf(field.elements[0])]) {
          if (key && spec.names![key]) return spec.names![key];
        }
        return undefined;
      }
      : undefined,
    labelOf: spec.labels ? (el) => keysOf(el).map((k) => spec.labels![k]).find(Boolean) ?? "" : undefined,
    steps: spec.steps,
    optionButtons: spec.optionButtons,
    dropdowns: spec.dropdowns,
  };
}

/** A page apply knows nothing about, on a site the person allowed: the biggest form, read by label. */
export const generic: Adapter = {
  board: "other",
  hosts: [],
  isForm: (_url, doc) => {
    const form = biggestForm(doc);
    return form !== null && !signInShowing(doc) && !THANKS.test(pageText(doc).slice(0, 3000));
  },
  isConfirmation: (_url, doc) => THANKS.test(pageText(doc).slice(0, 4000)),
  postingUrls: (url) => [...new Set([stripForm(url), `${url.protocol}//${url.host}${url.pathname}`])],
  root: (doc) => biggestForm(doc),
};
