/**
 * What goes where: each field's source (the board's own field names first, then label rules in English and
 * Nepali, then a saved answer whose question is the label), and the value or option it gets.
 *
 * Anything short of certain is left blank and listed: a blank is safe, a wrong answer isn't.
 */
import { bare, clean } from "./dom";
import type { Adapter, Action, FormField, PlanItem, Sheet, SheetAnswer, Source } from "./types";

type Rule = { test: RegExp; sources: Source[] };

const value = (key: Extract<Source, { type: "value" }>["key"]): Source => ({ type: "value", key });
const answer = (key: string): Source => ({ type: "answer", key });
const file = (document: string): Source => ({ type: "file", document });
const employer: Source = { type: "employer" };

// Agreeing, in Spanish. Matched anywhere in a label (\b doesn't treat "í" as a letter); over-matching only leaves a
// box for the person.
const CONSENT_ES = [
  "ley federal de protección de datos personales", "condiciones del servicio", "condiciones de servicio",
  "política de privacidad", "terminos y condiciones", "términos y condiciones", "politica de privacidad",
  "doy mi consentimiento", "tratamiento de datos", "términos de servicio", "aviso de privacidad",
  "proteccion de datos", "protección de datos", "condiciones de uso", "datos personales", "estoy de acuerdo",
  "términos de uso", "habeas data", "reconozco", "certifico", "consiento", "confirmo", "he leído", "autorizo",
  "he leido", "declaro", "lopdgdd", "acepto", "rgpd", "lopd",
];

/** Agreeing to terms or a privacy notice is the person's to do, never apply's. */
export const CONSENT = new RegExp(
  String.raw`\b(i (agree|consent|acknowledge|certify|confirm|understand)|privacy (policy|notice)|terms (of|and)|gdpr)\b|सहमत|`
    + CONSENT_ES.join("|"),
  "i",
);

/** Label rules, most specific first. */
export const RULES: Rule[] = [
  // "Have you ever previously been employed by the Texas A&M University System …?": the profile's employers.
  { test: /\b(ever|previously|formerly|before|in the past|prior)\b.{0,60}\b(employed|worked|work for|employee)\b|\b(former|previous|prior) (employee|worker)\b|\bhave you (ever )?worked (for|at)\b/i,
    sources: [employer] },
  // What kind of phone it is: nothing in a profile says, so it's left (the phone rule mustn't take it).
  { test: /phone (device )?type|type of phone/i, sources: [] },
  { test: /\bresume\b|\bcv\b|curriculum vitae|बायोडाटा/i, sources: [file("resume")] },
  { test: /cover letter|कभर लेटर/i, sources: [file("cover_letter")] },
  { test: /first name|given name|पहिलो नाम/i, sources: [value("first_name")] },
  { test: /last name|surname|family name|^थर$/i, sources: [value("last_name")] },
  { test: /^(your |full |legal )?name$|^full legal name$|पूरा नाम|^नाम$/i, sources: [value("full_name")] },
  { test: /e-?mail|इमेल/i, sources: [value("email")] },
  { test: /(country )?(phone|dialing|calling) code|country code|फोनको देश कोड/i, sources: [value("phone_country_code")] },
  { test: /phone|mobile|फोन|मोबाइल/i, sources: [value("phone")] },
  { test: /linkedin/i, sources: [value("linkedin"), answer("linkedin")] },
  { test: /github/i, sources: [value("github")] },
  { test: /portfolio|website|personal (site|url)|other website|पोर्टफोलियो|वेबसाइट/i,
    sources: [value("website"), answer("portfolio")] },
  { test: /sponsor|प्रायोजन/i, sources: [answer("needs_sponsorship")] },
  { test: /authori[sz]ed to work|legally (allowed|authori[sz]ed|eligible|able) to work|right to work|work permit|eligible to work|काम गर्ने कानुनी अनुमति/i,
    sources: [answer("work_authorization")] },
  { test: /notice period|सूचना अवधि/i, sources: [answer("notice_period")] },
  { test: /start date|when (can|could|would) you start|earliest (start|date)|available to start|सुरु गर्न/i,
    sources: [answer("start_date")] },
  { test: /salary|compensation|desired pay|pay expectation|तलब/i, sources: [answer("salary_expectation")] },
  { test: /relocat|बसाइँ/i, sources: [answer("relocate")] },
  { test: /how (did )?you (hear|heard|find|found|learn|learned)|heard about (us|this)|where did you (hear|find)|referral source|source of (this )?application|थाहा पाउनुभयो/i,
    sources: [answer("heard_from")] },
  { test: /\bgender\b|लिङ्ग/i, sources: [answer("gender")] },
  { test: /\brace\b|ethnicity|hispanic|latin[oax]|जाति/i, sources: [answer("ethnicity")] },
  { test: /veteran|पूर्वसैनिक/i, sources: [answer("veteran")] },
  { test: /disabilit|अपाङ्गता/i, sources: [answer("disability")] },
  { test: /current (company|employer|organi[sz]ation)|^company$|^organi[sz]ation$|^employer$/i,
    sources: [value("current_company")] },
  { test: /current (job )?(title|role|position)|^job title$|^title$/i, sources: [value("current_title")] },
  { test: /address (line )?(1|one)|street address|^street$|ठेगाना लाइन १/i, sources: [value("address_line1")] },
  { test: /address (line )?(2|two)|apartment|\bsuite\b|\bapt\b|ठेगाना लाइन २/i, sources: [value("address_line2")] },
  { test: /^city$|^town$|city\s*\/\s*town|^सहर$/i, sources: [value("city"), value("location")] },
  { test: /\bstate\b|province|\bregion\b|\bcounty\b|प्रदेश/i, sources: [value("region")] },
  { test: /postal|post ?code|\bzip\b|हुलाक कोड/i, sources: [value("postal_code")] },
  { test: /^country( of residence)?$|^देश$/i, sources: [value("country")] },
  { test: /\blocation\b|where are you (based|located)|current(ly)? (based|located)|^address$|ठेगाना|स्थान/i,
    sources: [value("location")] },
];

const DECLINE = /decline|don.?t wish|do not wish|prefer not|not (to )?(say|answer|disclose|self.?identify)|choose not|i do not want to answer|जवाफ दिन चाहन्नँ|prefiero no|no deseo|no quiero (responder|contestar|decirlo)|no contestar/i;

/** Words boards use for an answer's options, by its value: "woman" is often "Female". */
const SYNONYMS: Record<string, RegExp> = {
  yes: /^(yes|हो)\b/i,
  no: /^(no|होइन)\b/i,
  woman: /^(woman|female|महिला)\b/i,
  man: /^(man|male|पुरुष)\b/i,
  non_binary: /non.?binary|गैर-द्विलिङ्गी/i,
};
/** Veteran and disability options are sentences: what marks the yes and the no. */
const SENTENCE: Record<string, Record<string, RegExp>> = {
  veteran: { yes: /^(yes|i am a (protected )?veteran|i identify as)/i, no: /^(no|i am not)/i },
  disability: { yes: /^yes/i, no: /^no/i },
};

function normal(text: string): string {
  return bare(text).toLowerCase().replace(/[?:.]+$/, "").trim();
}

/** Where a field's value should come from, in order of preference, or [] if it isn't known. */
export function sourcesFor(field: FormField, sheet: Sheet, adapter: Adapter): Source[] {
  const hinted = adapter.hint?.(field);
  if (hinted?.length) return hinted;
  const label = normal(field.label);
  if (!label) return [];
  const rule = RULES.find((r) => r.test.test(label))?.sources ?? [];
  // A question saved word for word, answered, wins over a rule: the person wrote it for this. Unanswered, it's
  // only a fallback (the pack's saved answer mustn't hide the professional-network link in the profile).
  const exact = sheet.answers.find((a) => normal(a.question.en) === label || normal(a.question.ne) === label);
  if (exact) {
    const own = answer(exact.key);
    const others = rule.filter((s) => !(s.type === "answer" && s.key === exact.key));
    return exact.answer ? [own, ...others] : [...others, own];
  }
  if (rule.length) return rule;
  return [];
}

/** The employer a question names ("… employed by the Texas A&M University System, including …"), or "". */
export function employerNamed(label: string): string {
  const m = label.match(/\b(?:employed by|worked (?:for|at)|work for|employee of|been with)\s+(.+?)(?:\s*[,?(;]|\s+(?:includ|or any|as an?\b|in any)|$)/i);
  return m ? m[1]!.trim() : "";
}

const GENERIC_EMPLOYER = /^(us|this (company|organi[sz]ation|employer|firm)|our (company|organi[sz]ation)|the company|the organi[sz]ation)$/i;

/** An employer's name to compare: lower case, "&" as "and", without "the", "Inc.", "System" and the like. */
function employerKey(name: string): string {
  return ` ${name.toLowerCase().replace(/&/g, " and ").replace(/[^\p{L}\p{N}]+/gu, " ")} `
    .replace(/ (the|inc|llc|ltd|limited|plc|corp|corporation|co|company|group|system|systems|holdings) /g, " ")
    .replace(/\s+/g, " ").trim();
}

/** Whether the profile's employers include the one the question names (one name inside the other). */
export function workedFor(label: string, employers: string | undefined): boolean {
  const named = employerNamed(label);
  if (!named || GENERIC_EMPLOYER.test(named)) return false; // "worked for us": who "us" is isn't on the page
  const want = employerKey(named);
  if (want.length < 3) return false;
  return (employers ?? "").split("\n").map(employerKey).filter((e) => e.length >= 3)
    .some((e) => ` ${e} `.includes(` ${want} `) || ` ${want} `.includes(` ${e} `));
}

const YES: SheetAnswer = { key: "yes", question: { en: "", ne: "" }, answer_type: "yes_no", answer: "yes", choices: [], is_sensitive: false };

/** The answer a board's own dropdown wants, in words, for the person to choose. */
export function pickQuery(action: Extract<Action, { kind: "pick" }>): string {
  return action.answer ? textFor(action.answer) : action.value ?? "";
}

function findOption(field: FormField, saved: SheetAnswer): number {
  return optionFor(field.options, saved);
}

function optionFor(given: string[], saved: SheetAnswer): number {
  const options = given.map(clean);
  const real = options.map((o, i) => ({ o, i })).filter(({ o }) => o && !/^(select|choose|please select|--)/i.test(o));
  if (saved.answer === "decline" || saved.answer === "") {
    return real.find(({ o }) => DECLINE.test(o))?.i ?? -1;
  }
  const sentence = SENTENCE[saved.key]?.[saved.answer];
  if (sentence) {
    const hit = real.find(({ o }) => sentence.test(o) && !DECLINE.test(o));
    if (hit) return hit.i;
  }
  const choice = saved.choices.find((c) => c.value === saved.answer);
  const labels = [choice?.label.en, choice?.label.ne, saved.answer].filter(Boolean).map((l) => l!.toLowerCase());
  const exact = real.find(({ o }) => labels.includes(o.toLowerCase()));
  if (exact) return exact.i;
  const synonym = SYNONYMS[saved.answer];
  if (synonym) return real.find(({ o }) => synonym.test(o))?.i ?? -1;
  return -1;
}

function textFor(saved: SheetAnswer): string {
  if (saved.answer_type === "yes_no") return saved.answer === "yes" ? "Yes" : saved.answer === "no" ? "No" : "";
  if (saved.answer_type === "choice") {
    return saved.choices.find((c) => c.value === saved.answer)?.label.en ?? saved.answer;
  }
  return saved.answer;
}

function actionFor(field: FormField, sources: Source[], sheet: Sheet): Action {
  if (field.kind === "custom") return { kind: "blank", reason: "custom" };
  const choosing = field.kind === "select" || field.kind === "radio" || field.kind === "buttons";
  // Agreeing is the person's to do: a box that reads as consent is never ticked, whatever else it also asks
  // ("I'm authorised to work here and agree to the privacy policy"), and whatever answer is saved.
  if ((field.kind === "checkbox" || field.kind === "checkboxes") && CONSENT.test(field.label)) {
    return { kind: "blank", reason: "consent" };
  }
  if (sources.length === 0) return { kind: "blank", reason: "unknown" };
  // "unknown" until a source that suits this kind of field turns up empty (a cover-letter text box isn't a file).
  let reason: Extract<Action, { kind: "blank" }>["reason"] = "unknown";
  const missing = (why: typeof reason) => { if (reason === "unknown" || why !== "no_value") reason = why; };
  for (const source of sources) {
    if ((source.type === "file") !== (field.kind === "file")) continue;
    if (source.type === "employer") {
      if (!choosing && field.kind !== "dropdown") continue;
      if (!workedFor(field.label, sheet.values.past_employers)) { missing("no_value"); continue; }
      if (field.kind === "dropdown") return { kind: "pick", source, answer: YES };
      const i = findOption(field, YES);
      if (i >= 0) return { kind: "choose", option: i, source };
      missing("no_option");
      continue;
    }
    if (source.type === "file") {
      const doc = sheet.documents.find((d) => d.document_type === source.document);
      if (doc) return { kind: "attach", document: doc.document_type, filename: doc.filename };
      missing("no_value");
      continue;
    }
    if (source.type === "value") {
      if (field.kind === "checkbox" || field.kind === "checkboxes") continue;
      const v = sheet.values[source.key];
      if (!v) { missing("no_value"); continue; }
      if (field.kind === "dropdown") return { kind: "pick", source, value: v };
      if (field.kind === "select" || field.kind === "radio" || field.kind === "buttons") {
        const i = field.options.findIndex((o) => clean(o).toLowerCase() === v.toLowerCase());
        if (i >= 0) return { kind: "choose", option: i, source };
        missing("no_option");
        continue;
      }
      return { kind: "fill", value: v, source };
    }
    const saved = sheet.answers.find((a) => a.key === source.key);
    if (!saved) { missing("no_value"); continue; }
    const declined = saved.is_sensitive && (saved.answer === "decline" || saved.answer === "");
    if (field.kind === "dropdown") {
      if (!saved.answer && !declined) { missing("no_value"); continue; }
      return { kind: "pick", source, answer: saved };
    }
    if (field.kind === "select" || field.kind === "radio" || field.kind === "buttons") {
      const i = findOption(field, saved);
      if (i >= 0) return { kind: "choose", option: i, source };
      missing(declined ? "declined" : saved.answer ? "no_option" : "no_value");
      continue;
    }
    if (field.kind === "checkbox") {
      if (saved.answer_type === "yes_no" && saved.answer === "yes") return { kind: "check", source };
      missing(saved.answer ? "no_option" : "no_value");
      continue;
    }
    if (field.kind === "checkboxes") {
      // Several boxes (board03's equal-opportunity questions): only a decline is ticked, on the board's own option.
      const i = declined ? field.options.findIndex((o) => DECLINE.test(o)) : -1;
      if (i >= 0) return { kind: "choose", option: i, source };
      missing(declined ? "declined" : "custom");
      continue;
    }
    if (declined) { missing("declined"); continue; } // a free-text box: leaving it empty is declining
    const text = textFor(saved);
    if (text) return { kind: "fill", value: text, source };
    missing("no_value");
  }
  return { kind: "blank", reason };
}

/** What apply would do to each field. Nothing is changed yet. */
export function plan(fields: FormField[], sheet: Sheet, adapter: Adapter): PlanItem[] {
  return fields.map((field) => ({ field, action: actionFor(field, sourcesFor(field, sheet, adapter), sheet) }));
}
