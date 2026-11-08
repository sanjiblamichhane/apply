/** What a form is made of, and what apply puts in it. */
import type { Board as KnownBoard } from "./boards";

/** A board in boards.json, or "other": a site the person allowed, read by the label rules alone. */
export type Board = KnownBoard | "other";

export type FieldKind =
  | "text" | "email" | "tel" | "url" | "number" | "date" | "textarea"
  | "select" | "radio" | "checkbox" | "checkboxes" | "file"
  | "buttons" // one of the board's option buttons (board03's Yes / No), vouched for by its adapter
  | "dropdown" // the board's own list, opened to choose (board04's "Select One" button, its search box)
  | "custom"; // a control drawn by the board's own script (a combobox) that apply doesn't operate

/** A question on the form: one control, or a group of radios or checkboxes sharing a name. */
export interface FormField {
  /** Stable on the page: the element's id or name. */
  id: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  /** For select, radio and checkboxes: the text a person reads for each option. */
  options: string[];
  name: string;
  elements: HTMLElement[];
}

/** Profile values the backend's pack sends (GET /applications/{id}/fill → values). */
export type ValueKey =
  | "full_name" | "first_name" | "last_name" | "email" | "phone" | "phone_country_code" | "location"
  | "address_line1" | "address_line2" | "city" | "region" | "postal_code" | "country"
  | "linkedin" | "github" | "website" | "current_company" | "current_title"
  | "past_employers"; // every employer in the profile, one per line

/** Where a field's value comes from. Several are tried in order. */
export type Source =
  | { type: "value"; key: ValueKey }
  | { type: "answer"; key: string }
  | { type: "file"; document: string }
  // "Have you ever worked for <employer>?": yes when the profile's employers include the one it names.
  | { type: "employer" };

export interface Text { en: string; ne: string }

export interface SheetAnswer {
  key: string;
  question: Text;
  answer_type: "text" | "yes_no" | "choice" | "number" | "url";
  answer: string;
  choices: { value: string; label: Text }[];
  is_sensitive: boolean;
}

export interface SheetDocument {
  document_type: string;
  filename: string;
}

/** The fill sheet, as far as filling needs it. */
export interface Sheet {
  values: Partial<Record<ValueKey, string>>;
  answers: SheetAnswer[];
  documents: SheetDocument[];
}

/** Why a field was left for the person. */
export type BlankReason =
  | "unknown"      // apply doesn't know what the question is after
  | "no_value"     // it knows, but there's nothing saved for it
  | "no_option"    // the saved answer matches none of the form's options
  | "declined"     // a sensitive answer the person declines, on a field with no "decline" option
  | "consent"      // agreeing to terms is the person's to do
  | "custom"       // a control apply doesn't operate
  | "skipped";     // the person unticked it in the preview

export type Action =
  | { kind: "fill"; value: string; source: Source }
  | { kind: "choose"; option: number; source: Source }   // index into field.options
  | { kind: "check"; source: Source }
  | { kind: "attach"; document: string; filename: string }
  // A board's own dropdown: its options are only known once it's open, so what to look for is carried here.
  | { kind: "pick"; source: Source; answer?: SheetAnswer; value?: string }
  | { kind: "blank"; reason: BlankReason };

export interface PlanItem {
  field: FormField;
  action: Action;
}

/**
 * One field of the form as the preview shows it, before anything is written: what apply would put there, or why
 * it's left. `key` names the field across a preview and the fill that follows (ApplyOptions.skip).
 */
export interface PreviewRow {
  key: string;
  label: string;
  required: boolean;
  /** fill: text or a choice goes in; check: a box is ticked; attach: a file; kept: already has the person's entry;
   *  pick: the board's own list, for the person to choose (value: what to choose); blank: left (reason). */
  status: "fill" | "check" | "attach" | "kept" | "pick" | "blank";
  value?: string;
  reason?: BlankReason;
  /** An equal-opportunity answer: the panel hides its value until asked. */
  sensitive?: boolean;
}

export interface FillResult {
  filled: number;
  attached: string[];
  /** What was left for the person; suggestion: what to choose, for a dropdown the extension doesn't touch. */
  leftBlank: { label: string; reason: BlankReason; required: boolean; suggestion?: string }[];
}

export interface Adapter {
  board: Board;
  /** Hosts the board's forms live on: exact, or "*.suffix" (boards.json). */
  hosts: string[];
  /** The page is an application form (it may still be drawing it: see readForm). */
  isForm(url: URL, doc: Document): boolean;
  /** The board's "thank you, we've got it" page. */
  isConfirmation(url: URL, doc: Document): boolean;
  /** The URLs apply may know this posting by: the form's, and the posting's. */
  postingUrls(url: URL): string[];
  /** The form itself, or null while it isn't on the page yet. */
  root(doc: Document): ParentNode | null;
  /** Containers of one question each: one with no control apply can fill is listed as "custom". */
  questionSelector?: string;
  /** The board's own field names, before any label rule. */
  hint?(field: FormField): Source[] | undefined;
  /** What to call a control the page gives no label (board04's resume uploader), or "". */
  labelOf?(el: HTMLElement): string;
  /** Its form comes in steps (board04's My Information, My Experience, …): each is filled when it's showing. */
  steps?: boolean;
  /**
   * The board's own dropdowns (board04's "Select One" buttons and search boxes): read, never opened or pressed;
   * the person chooses, shown the answer to choose.
   */
  dropdowns?: string;
  /** The board's option buttons inside a question (board03's Yes / No): the only buttons ever pressed when filling. */
  optionButtons?: string;
}
