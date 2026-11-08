/**
 * Boards the extension fills by their addresses and the label rules (defineBoard), not yet for Auto: none has a
 * recorded form in fixtures/ yet. Each one's addresses as its career sites use them.
 */
import { defineBoard, stripForm } from "../define";
import type { Source, ValueKey } from "../types";

const value = (key: ValueKey): Source => ({ type: "value", key });

/**
 * board04: <tenant>.wd<N>.myworkdayjobs.com/[<locale>/]<site>/job/<place>/<title>_<id>/apply[/applyManually …],
 * and wd<N>.myworkdaysite.com/recruiting/<tenant>/<site>/job/…/apply. A sign-in (or create-account) step first,
 * then a form in steps (My Information, My Experience, Application Questions, …) drawn by script at one address.
 * Its controls are named by data-automation-id. Its dropdowns are its own: a "Select One" button that opens a
 * list, and a search box for "How Did You Hear About Us?". They're never opened or pressed: the person chooses,
 * shown the answer from their saved answers or profile.
 */
export const board04 = defineBoard({
  board: "board04",
  apply: /\/job\/.+\/apply(\/|$)/,
  posting: (url) => stripForm(new URL(url.href.replace(/\/apply(\/.*)?$/, ""))),
  form: "[data-automation-id=applyFlowPage]",
  questionSelector: "[data-automation-id^=formField-]",
  attribute: "data-automation-id",
  names: {
    legalNameSection_firstName: [value("first_name")],
    legalNameSection_lastName: [value("last_name")],
    email: [value("email")],
    "phone-number": [value("phone")],
    phoneNumber: [value("phone")],
    linkedinQuestion: [value("linkedin")],
    "file-upload-input-ref": [{ type: "file", document: "resume" }],
  },
  labels: { "file-upload-input-ref": "Resume/CV" },
  steps: true,
  dropdowns: "button[aria-haspopup=listbox], input[data-automation-id=searchBox]",
});

/** board05: jobs.smartrecruiters.com/<company>/<id>-<title>, and its one-click form under /oneclick-ui/. */
export const board05 = defineBoard({ board: "board05" });

/** board06: apply.workable.com/<account>/j/<shortcode>/apply/ (and /j/<shortcode>/apply). */
export const board06 = defineBoard({ board: "board06", apply: /\/j\/[A-Za-z0-9]+\/apply/ });

/** board07: <company>.recruitee.com/o/<slug>/c/new. */
export const board07 = defineBoard({ board: "board07", apply: /\/o\/[^/]+\/c\/new/ });

/** board08: <company>.jobs.personio.de/job/<id> (the form is on the posting's page). */
export const board08 = defineBoard({ board: "board08", apply: /\/job\/\d+/ });

/** board09: <company>.breezy.hr/p/<id>-<title>/apply. */
export const board09 = defineBoard({ board: "board09", apply: /\/p\/[^/]+\/apply/ });

/** board10: <company>.bamboohr.com/careers/<id> (the form opens on the posting's page). */
export const board10 = defineBoard({ board: "board10", apply: /\/careers\/\d+/ });

/** board11: <company>.teamtailor.com/jobs/<id>-<title>/applications/new. */
export const board11 = defineBoard({ board: "board11", apply: /\/jobs\/[^/]+\/applications/ });

/** board12: jobs.jobvite.com/<company>/job/<id>/apply. */
export const board12 = defineBoard({ board: "board12", apply: /\/job\/[^/]+\/apply/ });

/** board13: careers-<company>.icims.com/jobs/<id>/<title>/… (some companies draw the form in a frame). */
export const board13 = defineBoard({ board: "board13", apply: /\/jobs\/\d+/ });

/** board14: <company>.applytojob.com/apply/<id>/<title>. */
export const board14 = defineBoard({ board: "board14", apply: /\/apply\/[^/]+/ });

/** board15: ats.rippling.com/<company>/jobs/<id>/apply. */
export const board15 = defineBoard({ board: "board15", apply: /\/jobs\/[^/]+\/apply/ });

/** board16: www.dice.com/job-detail/<id>, applying on board16 after signing in (board16's own steps). */
export const board16 = defineBoard({ board: "board16", apply: /^\/(job-detail|apply|job-applications)\b/ });

export const MORE = [
  board04, board05, board06, board07, board08, board09, board10, board11, board12, board13, board14,
  board15, board16,
];
