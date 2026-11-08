/**
 * board01: job-boards.greenhouse.io (current) and boards.greenhouse.io (older, and its /embed/job_app).
 * The form is on the posting's own page; a sent one goes to …/confirmation.
 */
import { pageText } from "../dom";
import { known } from "../boards";
import type { Adapter, Source } from "../types";

const HOSTS = known("board01").hosts;
const JOB = /^\/([^/]+)\/jobs\/(\d+)/;

const NAMES: Record<string, Source[]> = {
  first_name: [{ type: "value", key: "first_name" }],
  last_name: [{ type: "value", key: "last_name" }],
  email: [{ type: "value", key: "email" }],
  phone: [{ type: "value", key: "phone" }],
  resume: [{ type: "file", document: "resume" }],
  cover_letter: [{ type: "file", document: "cover_letter" }],
  gender: [{ type: "answer", key: "gender" }],
  hispanic_ethnicity: [{ type: "answer", key: "ethnicity" }],
  race: [{ type: "answer", key: "ethnicity" }],
  veteran_status: [{ type: "answer", key: "veteran" }],
  disability_status: [{ type: "answer", key: "disability" }],
};

function job(url: URL): { board: string; id: string } | null {
  const m = JOB.exec(url.pathname);
  if (m) return { board: m[1]!, id: m[2]! };
  if (url.pathname.startsWith("/embed/job_app")) {
    const board = url.searchParams.get("for");
    const id = url.searchParams.get("token");
    if (board && id) return { board, id };
  }
  return null;
}

export const board01: Adapter = {
  board: "board01",
  ...known("board01"),
  isForm: (url, doc) => job(url) !== null && !/\/confirmation\/?$/.test(url.pathname)
    && doc.querySelector("#application-form, #application_form, form[action*='/applications']") !== null,
  isConfirmation: (url, doc) => job(url) !== null && (/\/confirmation\/?$/.test(url.pathname)
    || /thank you for applying|application (has been )?(submitted|received)/i.test(pageText(doc).slice(0, 4000))),
  postingUrls(url) {
    const found = job(url);
    if (!found) return [url.href];
    const own = `${url.protocol}//${url.host}/${found.board}/jobs/${found.id}`;
    const others = HOSTS.map((h) => `https://${h}/${found.board}/jobs/${found.id}`);
    return [...new Set([own, ...others])];
  },
  root: (doc) => doc.querySelector("#application-form, #application_form"),
  questionSelector: ".field, .application--question",
  hint: (field) => NAMES[field.id] ?? NAMES[field.name],
};
