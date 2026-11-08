/**
 * The content script on a board's pages (boards.json), and on any other site the person allowed (sites.ts):
 * describes the page, fills the form when the panel asks, and tells the service worker when the thank-you page
 * appears. On a site that isn't a board it reads the biggest form by its labels (the generic adapter). It
 * never submits anything.
 */
import { adapterFor, apply, formReady, generic, plan, preview, readForm, signature, signInShowing } from "@apply/ats-adapters";

import type { FileData, FillReply, PageChanged, PageInfo, ToBackground, ToContent } from "./messages";

const MAX_HTML = 3_000_000;
// Put on a page twice (declared, and again when the person allows the site): the first one answers.
const first = !(globalThis as { __apply?: boolean }).__apply;
(globalThis as { __apply?: boolean }).__apply = true;
const adapter = first ? (adapterFor(location.href, __BOARD_ALIASES__) ?? generic) : null;

function describe(): PageInfo | null {
  if (!adapter) return null;
  const url = new URL(location.href);
  const isForm = adapter.isForm(url, document);
  return {
    url: url.href,
    board: adapter.board,
    isForm,
    ready: formReady(document, adapter),
    isConfirmation: adapter.isConfirmation(url, document),
    signIn: signInShowing(document),
    steps: !!adapter.steps,
    formKey: isForm ? signature(readForm(document, adapter)) : "",
    postingUrls: adapter.postingUrls(url),
    title: document.title,
  };
}

function toFile(data: FileData): File {
  const bytes = Uint8Array.from(atob(data.base64), (c) => c.charCodeAt(0));
  return new File([bytes], data.filename, { type: "application/pdf" });
}

async function fill(message: Extract<ToContent, { type: "fill" }>): Promise<FillReply> {
  if (!adapter) return { ok: false, error: "unsupported" };
  try {
    const files = Object.fromEntries(message.files.map((f) => [f.document_type, toFile(f)]));
    const skip = new Set(message.skip ?? []);
    return { ok: true, result: apply(plan(readForm(document, adapter), message.sheet, adapter), { files, adapter, skip }) };
  } catch (error) {
    return { ok: false, error: String(error) };
  }
}

if (adapter) {
  chrome.runtime.onMessage.addListener((message: ToContent, _sender, reply) => {
    if (message.type === "page") reply(describe());
    else if (message.type === "preview") reply(preview(plan(readForm(document, adapter), message.sheet, adapter), message.sheet, adapter));
    else if (message.type === "html") reply(document.documentElement.outerHTML.slice(0, MAX_HTML));
    else if (message.type === "fill") {
      void fill(message).then(reply);
      return true; // the reply is sent from the promise
    }
  });

  // The thank-you page: on load (board01, board02) or drawn in place (board03). Told each time it appears.
  // And the panel, whenever what it shows would change without a page load: a board drawn by script moving to
  // another address (history.pushState), a sign-in step giving way to the form, a form's next step (board04).
  let showing = false;
  let seen = "";
  const check = () => {
    const info = describe();
    const now = !!info?.isConfirmation;
    if (now && !showing && info) {
      const message: ToBackground = { type: "confirmed", url: info.url };
      chrome.runtime.sendMessage(message).catch(() => undefined);
    }
    showing = now;
    const state = info ? [info.url, info.isForm, info.ready, info.signIn, info.isConfirmation, info.formKey].join("|") : "";
    if (seen && state !== seen) {
      const changed: PageChanged = { type: "page-changed" };
      chrome.runtime.sendMessage(changed).catch(() => undefined); // the panel may be closed
    }
    seen = state;
  };
  check();
  let queued = false;
  const soon = () => {
    if (queued) return;
    queued = true;
    setTimeout(() => { queued = false; check(); }, 300);
  };
  new MutationObserver(soon).observe(document.documentElement, { childList: true, subtree: true });
  addEventListener("popstate", soon);
}
