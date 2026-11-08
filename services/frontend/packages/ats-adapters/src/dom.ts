/**
 * Reading a form the way a person reads it: each control with the label they'd see, whether it's required,
 * and its options. Only standard DOM, so it runs in a content script, in jsdom, or injected by Playwright.
 */
import type { Adapter, FieldKind, FormField } from "./types";

/** Option buttons an adapter vouched for while reading the form: the only buttons filling may press. */
export const OPTION_BUTTONS = new WeakSet<Element>();
const SUBMIT_LIKE = /submit|apply|send|upload|next|continue|पठाउ/i;

const SKIPPED_TYPES = new Set(["hidden", "submit", "button", "reset", "image", "search", "password"]);
const REQUIRED_MARK = /[*✱]\s*$|\(required\)\s*$/i;

export function clean(text: string | null | undefined): string {
  return (text ?? "").replace(/\s+/g, " ").trim();
}

/** A label without the required marker ("First Name*" → "First Name"). */
export function bare(label: string): string {
  return clean(label.replace(/[*✱]/g, " ").replace(/\(required\)/gi, " "));
}

function textOf(el: Element | null | undefined): string {
  if (!el) return "";
  // A label's own text, without the text of controls inside it (a select's options, say).
  const copy = el.cloneNode(true) as Element;
  copy.querySelectorAll("select, option, textarea, input, script, style").forEach((n) => n.remove());
  return clean(copy.textContent);
}

/** Where an element's ids and label[for]s are looked up: its document, or the shadow root it's drawn in. */
type Scope = Document | ShadowRoot;
const scopeOf = (el: Element): Scope => el.getRootNode() as Scope;

function byIds(scope: Scope, ids: string | null): string {
  if (!ids) return "";
  return clean(ids.split(/\s+/).map((id) => textOf(scope.querySelector(`[id="${cssEscape(id)}"]`))).join(" "));
}

/**
 * querySelectorAll, also inside open shadow roots (forms drawn with web components, as board05'), in
 * page order. Closed shadow roots stay closed.
 */
export function deepAll<T extends Element>(root: ParentNode, selector: string): T[] {
  const found: T[] = [];
  const walk = (node: ParentNode) => {
    for (const el of Array.from(node.querySelectorAll("*"))) {
      if (el.matches(selector)) found.push(el as T);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(root);
  return found;
}

function cssEscape(value: string): string {
  return value.replace(/["\\]/g, "\\$&");
}

/** What a person would call this control. */
export function labelFor(el: HTMLElement, container?: Element | null): string {
  const scope = scopeOf(el);
  const labelled = byIds(scope, el.getAttribute("aria-labelledby"));
  if (labelled) return labelled;
  if (el.id) {
    const label = scope.querySelector(`label[for="${cssEscape(el.id)}"]`);
    if (label && textOf(label)) return textOf(label);
  }
  const wrapping = el.closest("label");
  if (wrapping && textOf(wrapping)) {
    // A board02 question wraps its label and control: prefer the label part.
    const part = wrapping.querySelector(".application-label, .label, legend");
    return textOf(part) || textOf(wrapping);
  }
  const aria = clean(el.getAttribute("aria-label"));
  if (aria) return aria;
  if (container) {
    const heading = container.querySelector("label, legend, .application-label, .label, .text");
    if (heading && textOf(heading)) return textOf(heading);
  }
  return clean(el.getAttribute("placeholder")) || clean(el.getAttribute("name"));
}

function groupLabel(el: HTMLElement, container: Element | null): string {
  const fieldset = el.closest("fieldset");
  const legend = fieldset?.querySelector("legend");
  if (container) {
    const heading = container.querySelector(".application-label, .label, legend")
      ?? Array.from(container.querySelectorAll("label")).find((l) => !l.querySelector("input"));
    if (heading && textOf(heading)) return textOf(heading);
  }
  if (legend && textOf(legend)) return textOf(legend);
  return byIds(scopeOf(el), el.closest("[role=radiogroup], [role=group]")?.getAttribute("aria-labelledby") ?? null)
    || clean(el.getAttribute("name"));
}

function kindOf(el: HTMLElement): FieldKind {
  if (el instanceof HTMLSelectElement) return "select";
  if (el instanceof HTMLTextAreaElement) return "textarea";
  if (el.getAttribute("role") === "combobox") return "custom";
  const type = (el.getAttribute("type") || "text").toLowerCase();
  if (["email", "tel", "url", "number", "date", "file", "radio", "checkbox"].includes(type)) return type as FieldKind;
  return "text";
}

function isRequired(el: HTMLElement, label: string, container?: Element | null): boolean {
  return el.hasAttribute("required") || el.getAttribute("aria-required") === "true" || REQUIRED_MARK.test(label)
    // board03 marks the label with a class and draws the asterisk with CSS.
    || !!container?.querySelector("label[class*=required], legend[class*=required]");
}

function hidden(el: HTMLElement): boolean {
  if (el.closest("[hidden], [aria-hidden=true]")) return true;
  if ((el as HTMLInputElement).disabled) return true;
  const style = el.getAttribute("style") ?? "";
  // A file input styled away behind the board's own "Attach" button is still the one to fill.
  return /display:\s*none/.test(style) && el.getAttribute("type") !== "file";
}

function optionText(input: HTMLInputElement): string {
  const scope = scopeOf(input);
  if (input.id) {
    const label = scope.querySelector(`label[for="${cssEscape(input.id)}"]`);
    if (label) return textOf(label);
  }
  const wrapping = input.closest("label");
  return wrapping ? textOf(wrapping) : clean(input.value);
}

/** Every question on the form, in page order. */
export function readForm(doc: Document, adapter: Adapter): FormField[] {
  const root = adapter.root(doc);
  if (!root) return [];
  const fields: FormField[] = [];
  const groups = new Map<string | Element, FormField>();
  const containerOf = (el: Element) => (adapter.questionSelector ? el.closest(adapter.questionSelector) : null);

  for (const el of deepAll<HTMLElement>(root, "input, select, textarea")) {
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (SKIPPED_TYPES.has(type) || hidden(el)) continue;
    const kind = adapter.dropdowns && el.matches(adapter.dropdowns) ? "dropdown" : kindOf(el);
    const name = el.getAttribute("name") ?? "";
    const container = containerOf(el);

    if (kind === "radio" || kind === "checkbox") {
      // One question: the inputs sharing a name, or (board03 names each checkbox after its option) one container.
      const sameName = name ? scopeOf(el).querySelectorAll(`input[name="${cssEscape(name)}"]`).length : 0;
      const several = sameName > 1
        || (!!container && container.querySelectorAll("input[type=radio], input[type=checkbox]").length > 1);
      const key = several && container && !(sameName > 1)
        ? container : name || el;
      const existing = groups.get(key);
      if (existing) {
        existing.elements.push(el);
        existing.options.push(optionText(el as HTMLInputElement));
        if (existing.kind === "checkbox") existing.kind = "checkboxes";
        existing.required ||= el.hasAttribute("required");
        continue;
      }
      const label = several ? groupLabel(el, container) : labelFor(el, container);
      if (!bare(label)) continue;
      const field: FormField = {
        id: name || el.id, label: bare(label), kind, required: isRequired(el, label, container),
        options: several ? [optionText(el as HTMLInputElement)] : [], name, elements: [el],
      };
      groups.set(key, field);
      fields.push(field);
      continue;
    }

    const label = labelFor(el, container) || adapter.labelOf?.(el) || "";
    if (!bare(label)) continue; // nothing a person could be told about (board03's "autofill from resume" uploader)
    fields.push({
      id: el.id || name,
      label: bare(label),
      kind,
      required: isRequired(el, label, container),
      options: el instanceof HTMLSelectElement
        ? Array.from(el.options).map((o) => clean(o.textContent))
        : [],
      name,
      elements: [el],
    });
  }

  // Questions answered with the board's own controls: its option buttons (board03's Yes / No) if the adapter
  // knows them, else listed for the person so they aren't missed.
  if (adapter.questionSelector) {
    for (const box of Array.from(root.querySelectorAll(adapter.questionSelector))) {
      const controls = Array.from(box.querySelectorAll<HTMLElement>("input:not([type=hidden]), select, textarea"));
      if (controls.some((c) => !hidden(c))) continue;
      const label = textOf(box.querySelector("label, legend, .application-label, .label, .text"));
      if (!label) continue;
      const dropdown = adapter.dropdowns ? box.querySelector<HTMLElement>(adapter.dropdowns) : null;
      if (dropdown && !hidden(dropdown)) {
        fields.push({
          id: dropdown.id || `dropdown:${bare(label)}`, label: bare(label), kind: "dropdown",
          required: REQUIRED_MARK.test(label) || dropdown.getAttribute("aria-required") === "true"
            || box.querySelector("[aria-required=true], [required]") !== null,
          options: [], name: "", elements: [dropdown],
        });
        continue;
      }
      const buttons = adapter.optionButtons
        ? Array.from(box.querySelectorAll<HTMLButtonElement>(adapter.optionButtons)).filter((b) => !SUBMIT_LIKE.test(clean(b.textContent)))
        : [];
      buttons.forEach((b) => OPTION_BUTTONS.add(b));
      fields.push({
        id: `custom:${bare(label)}`, label: bare(label), kind: buttons.length > 1 ? "buttons" : "custom",
        required: REQUIRED_MARK.test(label)
          || box.querySelector("[aria-required=true], [required], label[class*=required], legend[class*=required]") !== null,
        options: buttons.map((b) => clean(b.textContent)), name: "",
        elements: buttons.length > 1 ? buttons : [box as HTMLElement],
      });
    }
  }
  return fields;
}

/** True once the page has something an adapter can read (boards drawn by script need a moment). */
export function formReady(doc: Document, adapter: Adapter): boolean {
  const root = adapter.root(doc);
  return !!root && root.querySelector("input, select, textarea") !== null;
}

/** The text a person sees on the page: no scripts, styles or templates (a script may hold the thank-you text). */
export function pageText(doc: Document): string {
  if (!doc.body) return "";
  const copy = doc.body.cloneNode(true) as HTMLElement;
  copy.querySelectorAll("script, style, noscript, template").forEach((n) => n.remove());
  return clean(copy.textContent);
}

/** A sign-in (or create-an-account) form showing: the person signs in; it's never the application form. */
export function signInShowing(root: ParentNode | null): boolean {
  return !!root && Array.from(root.querySelectorAll<HTMLInputElement>("input[type=password]")).some((el) => !hidden(el));
}

/** A form's shape: its questions' labels, kinds and whether they're required (the extension notices a new step by it). */
export function signature(fields: FormField[]): string {
  const text = fields.map((f) => `${f.label}|${f.kind}|${f.required ? 1 : 0}`).join("\n");
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return `${fields.length}-${hash.toString(16).padStart(8, "0")}`;
}
