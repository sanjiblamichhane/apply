import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { adapterFor, apply, board03, boardHosts, fieldKey, board01, board02, plan, preview, readForm } from "../src";
import {
  board03FormMarkup, board03SuccessMarkup, board01Confirmation, board01Form, board02Confirmation, board02Form,
} from "../fixtures";
import { load, setFiles, sheet } from "./helpers";

const GH = "https://job-boards.greenhouse.io/acme/jobs/4012345";
const BOARD02 = "https://jobs.lever.co/himal/a1b2c3d4-0000-4000-8000-000000000001";
const BOARD03 = "https://jobs.ashbyhq.com/example-analytics/f3e1c2b4-1111-4111-8111-111111111111";

const files = {
  resume: new File(["%PDF-1.7 resume"], "Sam Rai – Resume.pdf", { type: "application/pdf" }),
  cover_letter: new File(["%PDF-1.7 letter"], "Sam Rai – Cover letter.pdf", { type: "application/pdf" }),
};

function byLabel(fields: ReturnType<typeof readForm>, label: string) {
  const found = fields.find((f) => f.label === label);
  if (!found) throw new Error(`no field ${label}: ${fields.map((f) => f.label).join(" | ")}`);
  return found;
}

let submitted: string[] = [];
let clicked: Element[] = [];
beforeEach(() => {
  submitted = [];
  clicked = [];
  vi.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => { submitted.push("submit()"); });
  vi.spyOn(HTMLFormElement.prototype, "requestSubmit").mockImplementation(() => { submitted.push("requestSubmit()"); });
  const click = HTMLElement.prototype.click;
  vi.spyOn(HTMLElement.prototype, "click").mockImplementation(function (this: HTMLElement) {
    clicked.push(this);
    click.call(this);
  });
  document.addEventListener("submit", (e) => { submitted.push("submit event"); e.preventDefault(); }, true);
});
afterEach(() => vi.restoreAllMocks());

function expectNothingSent() {
  expect(submitted).toEqual([]);
  for (const el of clicked) {
    const choice = el instanceof HTMLInputElement && ["radio", "checkbox"].includes(el.type);
    const option = el instanceof HTMLButtonElement && el.className.includes("_option_") && !/submit/i.test(el.textContent ?? "");
    expect(choice || option, `clicked ${el.outerHTML}`).toBe(true);
  }
}

describe("finding the board", () => {
  it("knows each board's hosts, and nothing else", () => {
    expect(adapterFor(`${GH}`)?.board).toBe("board01");
    expect(adapterFor("https://boards.greenhouse.io/embed/job_app?for=acme&token=4012345")?.board).toBe("board01");
    expect(adapterFor(`${BOARD02}/apply`)?.board).toBe("board02");
    expect(adapterFor(`${BOARD03}/application`)?.board).toBe("board03");
    expect(adapterFor("https://example.com/jobs/1")).toBeNull();
    expect(adapterFor("http://jobs.lever.co/himal/x")).toBeNull(); // https only
    expect(adapterFor("http://127.0.0.1:4011/acme/jobs/1", { "127.0.0.1:4011": "board01" })?.board).toBe("board01");
    expect(boardHosts()).toEqual(expect.arrayContaining(["job-boards.greenhouse.io", "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com"]));
  });

  it("gives the URLs apply may know a posting by", () => {
    expect(board01.postingUrls(new URL(`${GH}?gh_src=x`))).toEqual([GH, "https://boards.greenhouse.io/acme/jobs/4012345"]);
    expect(board01.postingUrls(new URL("https://boards.greenhouse.io/embed/job_app?for=acme&token=4012345")))
      .toEqual(["https://boards.greenhouse.io/acme/jobs/4012345", GH]);
    expect(board02.postingUrls(new URL(`${BOARD02}/apply?utm_source=newsletter`))).toEqual([BOARD02, `${BOARD02}/apply`]);
    expect(board03.postingUrls(new URL(`${BOARD03}/application`))).toEqual([BOARD03, `${BOARD03}/application`]);
  });

  it("tells the form from the thank-you page", () => {
    expect(board01.isForm(new URL(GH), load(board01Form(), GH))).toBe(true);
    expect(board01.isConfirmation(new URL(GH), document)).toBe(false);
    expect(board01.isConfirmation(new URL(`${GH}/confirmation`), load(board01Confirmation(), `${GH}/confirmation`))).toBe(true);
    expect(board02.isForm(new URL(`${BOARD02}/apply`), load(board02Form(), `${BOARD02}/apply`))).toBe(true);
    expect(board02.isConfirmation(new URL(`${BOARD02}/thanks`), load(board02Confirmation(), `${BOARD02}/thanks`))).toBe(true);
    const url = new URL(`${BOARD03}/application`);
    expect(board03.isConfirmation(url, load(`<div id=root>${board03FormMarkup()}</div>`, url.href))).toBe(false);
    expect(board03.isConfirmation(url, load(`<div id=root>${board03SuccessMarkup()}</div>`, url.href))).toBe(true);
  });
});

describe("board01", () => {
  it("reads every question with its label, kind and whether it's required", () => {
    const fields = readForm(load(board01Form(), GH), board01);
    expect(fields.map((f) => [f.label, f.kind, f.required])).toEqual([
      ["First Name", "text", true],
      ["Last Name", "text", true],
      ["Email", "email", true],
      ["Phone", "tel", false],
      ["Resume/CV", "file", true],
      ["Cover Letter", "file", false],
      ["LinkedIn Profile", "text", false],
      ["Website", "text", false],
      ["Are you legally authorized to work in the United States?", "select", true],
      ["Will you now or in the future require sponsorship for employment visa status (e.g. H-1B)?", "select", true],
      ["Why do you want to work at Acme Robotics?", "textarea", true],
      ["How did you hear about this job?", "text", false],
      ["Which office would you prefer?", "custom", false],
      ["Gender", "select", false],
      ["Are you Hispanic/Latino?", "select", false],
      ["Veteran Status", "select", false],
      ["Disability Status", "select", false],
      ["I agree to the processing of my personal data as described in the privacy policy.", "checkbox", true],
    ]);
    expect(byLabel(fields, "Gender").options).toEqual(["Select...", "Male", "Female", "Decline To Self Identify"]);
  });

  it("fills what it knows, attaches the documents, and leaves the rest for the person", () => {
    const doc = load(board01Form(), GH);
    const result = apply(plan(readForm(doc, board01), sheet(), board01), { files, setFiles });
    const value = (id: string) => (doc.getElementById(id) as HTMLInputElement).value;
    const chosen = (id: string) => {
      const select = doc.getElementById(id) as HTMLSelectElement;
      return select.options[select.selectedIndex]?.textContent;
    };
    expect([value("first_name"), value("last_name"), value("email"), value("phone")])
      .toEqual(["Sam", "Rai", "sam@example.com", "+977 980 000 0000"]);
    expect(value("question_31337001")).toBe("https://www.linkedin.com/in/example");
    expect(chosen("question_31337003")).toBe("Yes");
    expect(chosen("question_31337004")).toBe("No");
    expect(value("question_31337006")).toBe("apply");
    expect(chosen("gender")).toBe("Decline To Self Identify");
    expect(chosen("hispanic_ethnicity")).toBe("Decline To Self Identify");
    expect(chosen("veteran_status")).toBe("I am not a protected veteran");
    expect(chosen("disability_status")).toBe("I do not want to answer");
    expect((doc.getElementById("resume") as HTMLInputElement).files?.[0]?.name).toBe("Sam Rai – Resume.pdf");
    expect((doc.getElementById("gdpr_consent") as HTMLInputElement).checked).toBe(false);
    expect(result.attached).toEqual(["resume", "cover_letter"]);
    expect(result.leftBlank).toEqual([
      { label: "Website", reason: "no_value", required: false },
      { label: "Why do you want to work at Acme Robotics?", reason: "unknown", required: true },
      { label: "Which office would you prefer?", reason: "custom", required: false },
      { label: "I agree to the processing of my personal data as described in the privacy policy.", reason: "consent", required: true },
    ]);
    expect(result.filled).toBe(12); // and two files
    expectNothingSent();
  });

  it("never overwrites what the person typed", () => {
    const doc = load(board01Form(), GH);
    (doc.getElementById("email") as HTMLInputElement).value = "me@elsewhere.example";
    apply(plan(readForm(doc, board01), sheet(), board01), { files, setFiles });
    expect((doc.getElementById("email") as HTMLInputElement).value).toBe("me@elsewhere.example");
  });

  it("previews what it would fill without touching the form, and agrees with the fill", () => {
    const doc = load(board01Form(), GH);
    (doc.getElementById("phone") as HTMLInputElement).value = "+1 555 0100";
    const before = doc.body.innerHTML;
    const rows = preview(plan(readForm(doc, board01), sheet(), board01), sheet(), board01);
    expect(doc.body.innerHTML).toBe(before); // read only
    const row = (label: string) => rows.find((r) => r.label === label);
    expect(row("First Name")).toMatchObject({ status: "fill", value: "Sam", required: true });
    expect(row("Phone")).toMatchObject({ status: "kept" }); // the person's entry stays
    expect(row("Resume/CV")).toMatchObject({ status: "attach", value: "Sam Rai – Resume.pdf" });
    expect(row("Are you legally authorized to work in the United States?")).toMatchObject({ status: "fill", value: "Yes" });
    expect(row("Gender")).toMatchObject({ status: "fill", value: "Decline To Self Identify", sensitive: true });
    expect(row("Which office would you prefer?")).toMatchObject({ status: "blank", reason: "custom" });
    expect(row("I agree to the processing of my personal data as described in the privacy policy."))
      .toMatchObject({ status: "blank", reason: "consent" });
    const result = apply(plan(readForm(doc, board01), sheet(), board01), { files, setFiles });
    expect(result.filled + result.attached.length).toBe(rows.filter((r) => ["fill", "check", "attach"].includes(r.status)).length);
  });

  it("leaves a field the person unticked, and says so", () => {
    const doc = load(board01Form(), GH);
    const fields = readForm(doc, board01);
    const skip = new Set([fieldKey(fields.find((f) => f.label === "Email")!)]);
    const result = apply(plan(fields, sheet(), board01), { files, setFiles, skip });
    expect((doc.getElementById("email") as HTMLInputElement).value).toBe("");
    expect((doc.getElementById("first_name") as HTMLInputElement).value).toBe("Sam");
    expect(result.leftBlank).toContainEqual({ label: "Email", reason: "skipped", required: true });
  });
});

describe("board02", () => {
  it("reads links, cards, radios and equal-opportunity questions", () => {
    const fields = readForm(load(board02Form(), `${BOARD02}/apply`), board02);
    expect(fields.map((f) => [f.label, f.kind, f.required])).toEqual([
      ["Resume/CV", "file", true],
      ["Full name", "text", true],
      ["Email", "email", true],
      ["Phone", "text", false],
      ["Current location", "text", false],
      ["Current company", "text", false],
      ["LinkedIn URL", "text", false],
      ["GitHub URL", "text", false],
      ["Portfolio URL", "text", false],
      ["Other website", "text", false],
      ["What is your notice period?", "text", true],
      ["Are you willing to relocate to Kathmandu?", "radio", true],
      ["Tell us about a project you are proud of", "textarea", false],
      ["Add a cover letter or anything else you want to share.", "textarea", false],
      ["Gender", "select", false],
      ["Race", "select", false],
      ["Veteran status", "select", false],
    ]);
    expect(byLabel(fields, "Are you willing to relocate to Kathmandu?").options).toEqual(["Yes", "No"]);
  });

  it("fills it, choosing radios by their text", () => {
    const doc = load(board02Form(), `${BOARD02}/apply`);
    const result = apply(plan(readForm(doc, board02), sheet(), board02), { files, setFiles });
    const named = (name: string) => doc.querySelector(`[name="${name}"]`) as HTMLInputElement;
    expect(named("name").value).toBe("Sam Rai");
    expect(named("org").value).toBe("Himal Tech");
    expect(named("urls[LinkedIn]").value).toBe("https://www.linkedin.com/in/example");
    expect(named("urls[GitHub]").value).toBe("https://github.com/example");
    expect(named("cards[0b1c][field0]").value).toBe("One month");
    expect((doc.querySelector('input[value="Yes"]') as HTMLInputElement).checked).toBe(true);
    expect((named("eeo[gender]") as unknown as HTMLSelectElement).value).toBe("Decline to self-identify");
    expect((named("eeo[veteran]") as unknown as HTMLSelectElement).value).toBe("I am not a veteran");
    expect(result.leftBlank.map((b) => [b.label, b.reason])).toEqual([
      ["Current location", "no_value"],
      ["Portfolio URL", "no_value"],
      ["Other website", "no_value"],
      ["Tell us about a project you are proud of", "unknown"],
      ["Add a cover letter or anything else you want to share.", "unknown"],
    ]);
    expectNothingSent();
  });
});

describe("board03", () => {
  it("fills a React-drawn form the way React notices, and lists its own controls", () => {
    const doc = load(`<div id=root>${board03FormMarkup()}</div>`, `${BOARD03}/application`);
    // A stand-in for React: it keeps only values that arrive with an input event.
    const state: Record<string, string> = {};
    doc.querySelector(".ashby-application-form-container")!.addEventListener("input", (e) => {
      const target = e.target as HTMLInputElement;
      state[target.name] = target.value;
    });
    const fields = readForm(doc, board03);
    expect(fields.map((f) => [f.label, f.kind, f.required])).toEqual([
      ["Name", "text", true], ["Email", "email", true], ["Resume", "file", true], ["Phone Number", "tel", false],
      ["LinkedIn Profile", "text", false], ["What is your notice period?", "text", false], ["Why Example Analytics?", "textarea", false],
      ["Race/ethnicity", "checkboxes", false], ["Will you require visa sponsorship?", "buttons", true],
    ]);
    expect(fields.find((f) => f.kind === "buttons")!.options).toEqual(["Yes", "No"]);
    expect(fields.find((f) => f.label === "Race/ethnicity")!.options).toEqual(["Asian or Asian American", "White", "Other", "I prefer not to answer"]);
    const result = apply(plan(fields, sheet(), board03), { files, setFiles });
    expect(state).toMatchObject({
      _systemfield_name: "Sam Rai", _systemfield_email: "sam@example.com", "4f1e0d6c-phone": "+977 980 000 0000",
      "9a2b-linkedin": "https://www.linkedin.com/in/example", "7c3d-notice": "One month",
    });
    expect(result.attached).toEqual(["resume"]);
    expect((doc.getElementById("ae95_1e21-labeled-checkbox-3") as HTMLInputElement).checked).toBe(true); // declined
    expect((doc.getElementById("ae95_1e21-labeled-checkbox-0") as HTMLInputElement).checked).toBe(false);
    expect(result.leftBlank).toEqual([{ label: "Why Example Analytics?", reason: "unknown", required: false }]);
    expect(clicked.map((b) => b.textContent)).toContain("No"); // needs_sponsorship: no, on the board's own button
    expect(clicked.some((b) => /Submit|Upload/.test(b.textContent ?? ""))).toBe(false);
    expectNothingSent();
  });
});

it("doesn't take a thank-you inside a script for the thank-you page", () => {
  const url = `${BOARD03}/application`;
  const doc = load(`<div id=root><p>Loading…</p></div><script>const done = "Thank you for applying!";</script>`, url);
  expect(board03.isConfirmation(new URL(url), doc)).toBe(false);
});

describe("noticing a new step", () => {
  it("gives a form a signature that changes when its questions do", async () => {
    const { signature } = await import("../src");
    const first = signature(readForm(load(board01Form(), GH), board01));
    expect(signature(readForm(load(board01Form(), GH), board01))).toBe(first);
    const changed = board01Form().replace("How did you hear about this job?", "Who referred you?");
    expect(signature(readForm(load(changed, GH), board01))).not.toBe(first);
  });

  it("never takes a submit-like button for an option", () => {
    const html = `<div class="ashby-application-form-container"><div class="ashby-application-form-field-entry">
      <label>Will you relocate?</label><div><button type="submit" class="_option_1">Yes</button>
      <button type="submit" class="_option_1">Submit Application</button></div></div></div>`;
    const [field] = readForm(load(html, `${BOARD03}/application`), board03);
    expect(field!.kind).toBe("custom"); // one real option isn't a choice: left for the person
  });
});
