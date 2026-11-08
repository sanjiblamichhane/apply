import { describe, expect, it } from "vitest";

import { board01, plan, readForm, sourcesFor, type FormField } from "../src";
import { load, sheet } from "./helpers";

function field(label: string, kind: FormField["kind"] = "text", options: string[] = []): FormField {
  return { id: label, label, kind, required: false, options, name: "", elements: [] };
}

describe("matching a label to a source", () => {
  it("knows the questions in English and Nepali", () => {
    const s = sheet();
    const key = (label: string) => sourcesFor(field(label), s, board01)[0];
    expect(key("पहिलो नाम")).toEqual({ type: "value", key: "first_name" });
    expect(key("इमेल")).toEqual({ type: "value", key: "email" });
    expect(key("तपाईंको सूचना अवधि कति हो?")).toEqual({ type: "answer", key: "notice_period" });
    expect(key("Do you require visa sponsorship?")).toEqual({ type: "answer", key: "needs_sponsorship" });
    expect(key("Earliest start date")).toEqual({ type: "answer", key: "start_date" });
    expect(key("Where are you based?")).toEqual({ type: "value", key: "location" });
    expect(key("Are you willing to relocate?")).toEqual({ type: "answer", key: "relocate" });
    expect(key("Please tell us how you heard about this opportunity.")).toEqual({ type: "answer", key: "heard_from" });
    expect(key("Favourite colour")).toBeUndefined();
  });

  it("knows an address in its parts, and a phone's country code from the phone", () => {
    const s = sheet();
    const key = (label: string) => sourcesFor(field(label), s, board01)[0];
    expect(key("Address Line 1")).toEqual({ type: "value", key: "address_line1" });
    expect(key("Street address")).toEqual({ type: "value", key: "address_line1" });
    expect(key("Address line 2")).toEqual({ type: "value", key: "address_line2" });
    expect(key("City")).toEqual({ type: "value", key: "city" });
    expect(sourcesFor(field("City"), s, board01)[1]).toEqual({ type: "value", key: "location" }); // else
    expect(key("State / Province")).toEqual({ type: "value", key: "region" });
    expect(key("Postal Code")).toEqual({ type: "value", key: "postal_code" });
    expect(key("ZIP")).toEqual({ type: "value", key: "postal_code" });
    expect(key("Country")).toEqual({ type: "value", key: "country" });
    expect(key("Country Phone Code")).toEqual({ type: "value", key: "phone_country_code" });
    expect(key("Phone Number")).toEqual({ type: "value", key: "phone" });
    // Not an address: the United States in a work question stays that question's.
    expect(key("Are you legally authorized to work in the United States?")).toEqual({ type: "answer", key: "work_authorization" });
  });

  it("prefers a question the person saved word for word", () => {
    const s = sheet({
      answers: [...sheet().answers, {
        key: "pets", question: { en: "Do you like robots?", ne: "रोबोट मन पर्छ?" }, answer_type: "yes_no",
        answer: "yes", choices: [], is_sensitive: false,
      }],
    });
    expect(sourcesFor(field("Do you like robots"), s, board01)).toEqual([{ type: "answer", key: "pets" }]);
    expect(sourcesFor(field("रोबोट मन पर्छ?"), s, board01)).toEqual([{ type: "answer", key: "pets" }]);
  });
});

describe("choosing an option", () => {
  const choose = (label: string, options: string[], overrides: Parameters<typeof sheet>[0] = {}) =>
    plan([field(label, "select", options)], sheet(overrides), board01)[0]!.action;

  it("finds the board's own words for decline", () => {
    for (const decline of ["I don't wish to answer", "Prefer not to say", "Decline to self-identify", "I do not want to answer"]) {
      expect(choose("Gender", ["Select...", "Male", "Female", decline])).toMatchObject({ kind: "choose", option: 3 });
    }
  });

  it("leaves a sensitive question blank when the form has no way to decline", () => {
    expect(choose("Gender", ["Select...", "Male", "Female"])).toEqual({ kind: "blank", reason: "declined" });
  });

  it("matches a provided answer by synonyms, and never guesses", () => {
    const answers = sheet().answers.map((a) => (a.key === "gender" ? { ...a, answer: "woman" } : a));
    expect(choose("Gender", ["Select...", "Male", "Female"], { answers })).toMatchObject({ kind: "choose", option: 2 });
    expect(choose("Gender", ["Select...", "Option A", "Option B"], { answers })).toEqual({ kind: "blank", reason: "no_option" });
  });

  it("answers yes/no questions in a text box with words", () => {
    expect(plan([field("Are you authorised to work in the UK?")], sheet(), board01)[0]!.action)
      .toMatchObject({ kind: "fill", value: "Yes" });
  });
});

it("never ticks consent, even with everything known", () => {
  const doc = load(`<form id="application-form"><div class="field"><input type="checkbox" id="c" name="c">
    <label for="c">I certify that the information is true</label></div></form>`, "https://job-boards.greenhouse.io/a/jobs/1");
  const [item] = plan(readForm(doc, board01), sheet(), board01);
  expect(item!.action).toEqual({ kind: "blank", reason: "consent" });
});

it("never ticks consent folded into a question it can answer (security review)", () => {
  // Saved "yes" to "authorised to work", but the same box also agrees to a policy: agreeing is the person's.
  const label = "I confirm I am legally authorized to work in the US and agree to the Privacy Policy";
  expect(plan([field(label, "checkbox")], sheet(), board01)[0]!.action).toEqual({ kind: "blank", reason: "consent" });
  expect(plan([field(label, "checkboxes", ["Yes"])], sheet(), board01)[0]!.action)
    .toEqual({ kind: "blank", reason: "consent" });
  // A plain yes/no box about the right to work is still answered from the saved answer.
  expect(plan([field("I am authorised to work in the UK", "checkbox")], sheet(), board01)[0]!.action)
    .toMatchObject({ kind: "check" });
});

it("lets an unanswered saved question fall back to the profile", () => {
  const s = sheet({
    answers: [...sheet().answers, { key: "linkedin", question: { en: "Professional network profile", ne: "पेसागत सञ्जाल प्रोफाइल" },
      answer_type: "url", answer: "", choices: [], is_sensitive: false }],
  });
  expect(plan([field("LinkedIn Profile")], s, board01)[0]!.action)
    .toMatchObject({ kind: "fill", value: "https://www.linkedin.com/in/example" });
});

it("never ticks consent in Spanish either", () => {
  for (const label of [
    "Acepto la Política de Privacidad",
    "He leído y acepto los términos y condiciones",
    "Doy mi consentimiento para el tratamiento de mis datos personales",
    "Confirmo que estoy autorizado a trabajar en España",
  ]) {
    expect(plan([field(label, "checkbox")], sheet(), board01)[0]!.action, label).toEqual({ kind: "blank", reason: "consent" });
  }
});
