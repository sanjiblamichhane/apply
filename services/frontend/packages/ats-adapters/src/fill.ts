/**
 * Putting the plan into the form the way a person's typing would: the browser's own value setter, then the
 * input, change and blur events a page listens for (React-drawn forms such as board03's only see a value that
 * arrives like that). Files are attached through a DataTransfer.
 *
 * It never presses Submit, never submits the form, and never overwrites something already typed in. The only
 * clicks are on radio buttons and checkboxes (the one way some pages notice them being chosen) and on option
 * buttons the board's adapter vouched for while reading the form (board03's Yes / No).
 *
 * A board's own dropdown (board04's "Select One" lists and searches) is never opened, typed into or pressed:
 * that would mean imitating keys and clicks inside the board's own widgets, which its page can take for a bot
 * and get into a state its server refuses. It's left for the person, with the answer to choose beside it.
 */
import { clean, OPTION_BUTTONS } from "./dom";
import { pickQuery } from "./match";
import type { Adapter, FillResult, FormField, PlanItem, PreviewRow, Sheet, Source } from "./types";

const PLACEHOLDER = /^(select one|select|choose one|choose|please select|--+|)$/i;

/** Whether a board's own dropdown shows a choice already: its button's text, or a search's chosen chip. Read only. */
function pickedAlready(field: FormField, adapter?: Adapter): boolean {
  const el = field.elements[0]!;
  if (el instanceof HTMLInputElement) {
    const box = el.closest(adapter?.questionSelector ?? "*") ?? el.parentElement;
    return Boolean(box?.querySelector("[data-automation-id=selectedItem], [aria-selected=true]"));
  }
  return !PLACEHOLDER.test(clean(el.textContent));
}

export interface ApplyOptions {
  /** The files for each document type (the extension makes them from the PDFs). */
  files?: Record<string, File>;
  /** How to put files on an input; jsdom has no DataTransfer, so tests pass their own. */
  setFiles?: (input: HTMLInputElement, files: File[]) => void;
  /** The board's adapter, to see what its own dropdowns show. */
  adapter?: Adapter;
  /** Fields the person unticked in the preview (PreviewRow.key): left as they are, and listed as left. */
  skip?: ReadonlySet<string>;
}

/** A field's name across a preview and the fill after it: its id, and its label in case two share an id. */
export const fieldKey = (field: FormField): string => `${field.id}|${field.label}`;

function fire(el: Element, ...types: string[]): void {
  for (const type of types) {
    const event = type === "blur" ? new FocusEvent("focusout", { bubbles: true }) : new Event(type, { bubbles: true });
    el.dispatchEvent(event);
  }
}

/** As typing leaves it: focused, the value set the way the browser sets it, input and change, then left. */
function setValue(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, value: string): void {
  const proto = el instanceof HTMLTextAreaElement
    ? HTMLTextAreaElement.prototype
    : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  el.focus?.();
  if (setter) setter.call(el, value);
  else el.value = value;
  fire(el, "input", "change");
  fire(el, "blur");
  el.blur?.();
}

/** A click, but only ever on a radio button, a checkbox, or a vouched-for option button. */
function choose(input: HTMLElement): void {
  if (input instanceof HTMLButtonElement && OPTION_BUTTONS.has(input)) {
    input.click();
    return;
  }
  if (!(input instanceof HTMLInputElement) || !["radio", "checkbox"].includes(input.type)) {
    throw new Error("apply only clicks radio buttons, checkboxes and a board's option buttons");
  }
  if (!input.checked) input.click();
  if (!input.checked) { input.checked = true; fire(input, "input", "change"); }
}

function defaultSetFiles(input: HTMLInputElement, files: File[]): void {
  const transfer = new DataTransfer();
  for (const f of files) transfer.items.add(f);
  input.files = transfer.files;
}

function hasValue(el: HTMLElement): boolean {
  if (el instanceof HTMLButtonElement) return el.getAttribute("aria-pressed") === "true";
  if (el instanceof HTMLSelectElement) return el.selectedIndex > 0 && !!el.value;
  if (el instanceof HTMLInputElement && el.type === "file") return (el.files?.length ?? 0) > 0;
  if (el instanceof HTMLInputElement && (el.type === "radio" || el.type === "checkbox")) return el.checked;
  return !!(el as HTMLInputElement).value?.trim();
}

/** Carry out the plan. Returns what was filled and what was left for the person (with why). */
export function apply(items: PlanItem[], options: ApplyOptions = {}): FillResult {
  const result: FillResult = { filled: 0, attached: [], leftBlank: [] };
  const setFiles = options.setFiles ?? defaultSetFiles;
  for (const { field, action } of items) {
    const [first] = field.elements;
    if (!first) continue;
    if (field.kind === "dropdown" && pickedAlready(field, options.adapter)) continue; // the person chose
    if (options.skip?.has(fieldKey(field)) && action.kind !== "blank") {
      if (!field.elements.some(hasValue)) result.leftBlank.push({ label: field.label, reason: "skipped", required: field.required });
      continue;
    }
    if (action.kind === "blank") {
      if (!field.elements.some(hasValue)) {
        result.leftBlank.push({ label: field.label, reason: action.reason, required: field.required });
      }
      continue;
    }
    if (field.elements.some(hasValue)) continue; // the person's own entry stays
    if (action.kind === "fill") {
      setValue(first as HTMLInputElement, action.value);
      result.filled += 1;
    } else if (action.kind === "choose") {
      if (first instanceof HTMLSelectElement) {
        const option = first.options[action.option];
        if (!option) continue;
        setValue(first, option.value);
      } else {
        const radio = field.elements[action.option];
        if (!radio) continue;
        choose(radio);
      }
      result.filled += 1;
    } else if (action.kind === "check") {
      choose(first);
      result.filled += 1;
    } else if (action.kind === "pick") {
      // A board's own dropdown: the person chooses, with what to choose shown to them.
      const suggestion = pickQuery(action);
      result.leftBlank.push({ label: field.label, reason: "custom", required: field.required, ...(suggestion ? { suggestion } : {}) });
    } else if (action.kind === "attach") {
      const file = options.files?.[action.document];
      if (!file || !(first instanceof HTMLInputElement)) {
        result.leftBlank.push({ label: field.label, reason: "no_value", required: field.required });
        continue;
      }
      setFiles(first, [file]);
      fire(first, "input", "change");
      result.attached.push(action.document);
    }
  }
  return result;
}

function sensitive(source: Source, sheet: Sheet): boolean {
  return source.type === "answer" && !!sheet.answers.find((a) => a.key === source.key)?.is_sensitive;
}

/**
 * What apply() would do with the plan, read only: each field with the value that would go in, or why it's left.
 * Follows apply()'s own rules (the person's entry stays; a board's own list is theirs to choose), so the preview
 * and the fill agree.
 */
export function preview(items: PlanItem[], sheet: Sheet, adapter?: Adapter): PreviewRow[] {
  const rows: PreviewRow[] = [];
  for (const { field, action } of items) {
    if (!field.elements[0]) continue;
    const base = { key: fieldKey(field), label: field.label, required: field.required };
    const kept = field.kind === "dropdown" ? pickedAlready(field, adapter) : field.elements.some(hasValue);
    if (kept) { rows.push({ ...base, status: "kept" }); continue; }
    switch (action.kind) {
      case "blank":
        rows.push({ ...base, status: "blank", reason: action.reason });
        break;
      case "fill":
        rows.push({ ...base, status: "fill", value: action.value, sensitive: sensitive(action.source, sheet) });
        break;
      case "choose":
        rows.push({ ...base, status: "fill", value: field.options[action.option] ?? "", sensitive: sensitive(action.source, sheet) });
        break;
      case "check":
        rows.push({ ...base, status: "check", sensitive: sensitive(action.source, sheet) });
        break;
      case "attach":
        rows.push({ ...base, status: "attach", value: action.filename });
        break;
      case "pick": {
        const suggestion = pickQuery(action);
        rows.push({ ...base, status: "pick", ...(suggestion ? { value: suggestion } : {}), sensitive: sensitive(action.source, sheet) });
        break;
      }
    }
  }
  return rows;
}
