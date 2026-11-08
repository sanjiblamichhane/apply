/**
 * board02: /{company}/{posting}/apply on its host; a sent one goes to …/thanks. Links are urls[<network>] and
 * the like, extra questions are "cards", and equal-opportunity questions are eeo[…].
 */
import { pageText } from "../dom";
import { known } from "../boards";
import type { Adapter, Source } from "../types";

const POSTING = /^\/([^/]+)\/([0-9a-f-]{36})(?:\/(apply|thanks))?\/?$/i;

const NAMES: Record<string, Source[]> = {
  name: [{ type: "value", key: "full_name" }],
  email: [{ type: "value", key: "email" }],
  phone: [{ type: "value", key: "phone" }],
  location: [{ type: "value", key: "location" }],
  org: [{ type: "value", key: "current_company" }],
  resume: [{ type: "file", document: "resume" }],
  "urls[LinkedIn]": [{ type: "value", key: "linkedin" }, { type: "answer", key: "linkedin" }],
  "urls[GitHub]": [{ type: "value", key: "github" }],
  "urls[Portfolio]": [{ type: "value", key: "website" }, { type: "answer", key: "portfolio" }],
  "eeo[gender]": [{ type: "answer", key: "gender" }],
  "eeo[race]": [{ type: "answer", key: "ethnicity" }],
  "eeo[veteran]": [{ type: "answer", key: "veteran" }],
  "eeo[disability]": [{ type: "answer", key: "disability" }],
};

export const board02: Adapter = {
  board: "board02",
  ...known("board02"),
  isForm: (url, doc) => POSTING.exec(url.pathname)?.[3]?.toLowerCase() === "apply"
    && doc.querySelector("#application-form, form[action$='/apply']") !== null,
  isConfirmation: (url, doc) => POSTING.exec(url.pathname)?.[3]?.toLowerCase() === "thanks"
    || (POSTING.test(url.pathname) && /application submitted|thanks for applying/i.test(pageText(doc).slice(0, 4000))),
  postingUrls(url) {
    const m = POSTING.exec(url.pathname);
    if (!m) return [url.href];
    const posting = `${url.protocol}//${url.host}/${m[1]}/${m[2]}`;
    return [posting, `${posting}/apply`];
  },
  root: (doc) => doc.querySelector("#application-form, form[action$='/apply']"),
  questionSelector: ".application-question",
  hint: (field) => NAMES[field.name],
};
