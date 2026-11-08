/**
 * board03: jobs.ashbyhq.com/{company}/{posting}/application. The page draws its form with React after it loads
 * (in a container, not a <form>), and says thank you in place once sent (the address doesn't change). System
 * fields are _systemfield_…; required questions have a class on their label, the asterisk is CSS.
 */
import { pageText } from "../dom";
import { known } from "../boards";
import type { Adapter, Source } from "../types";

const POSTING = /^\/([^/]+)\/([0-9a-f-]{36})(?:\/(application))?\/?$/i;

const NAMES: Record<string, Source[]> = {
  _systemfield_name: [{ type: "value", key: "full_name" }],
  _systemfield_email: [{ type: "value", key: "email" }],
  _systemfield_phone: [{ type: "value", key: "phone" }],
  _systemfield_location: [{ type: "value", key: "location" }],
  _systemfield_resume: [{ type: "file", document: "resume" }],
  _systemfield_cover_letter: [{ type: "file", document: "cover_letter" }],
};

const THANKS = /thank(s| you) for applying|application (was |has been )?(submitted|received)/i;

export const board03: Adapter = {
  board: "board03",
  ...known("board03"),
  isForm: (url) => POSTING.exec(url.pathname)?.[3]?.toLowerCase() === "application",
  isConfirmation: (url, doc) => POSTING.test(url.pathname)
    && (doc.querySelector(".ashby-application-form-success-container") !== null
      || (doc.querySelector(".ashby-application-form-container") === null && THANKS.test(pageText(doc).slice(0, 4000)))),
  postingUrls(url) {
    const m = POSTING.exec(url.pathname);
    if (!m) return [url.href];
    const posting = `${url.protocol}//${url.host}/${m[1]}/${m[2]}`;
    return [posting, `${posting}/application`];
  },
  root: (doc) => doc.querySelector(".ashby-application-form-container"), // no <form>: React posts it itself
  questionSelector: ".ashby-application-form-field-entry",
  hint: (field) => NAMES[field.id] ?? NAMES[field.name],
  optionButtons: "button[class*=_option_]",
};
