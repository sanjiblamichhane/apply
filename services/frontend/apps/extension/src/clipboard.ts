/**
 * Putting a value on the clipboard from the side panel. The write starts inside the click, before anything is
 * awaited: the browser refuses a page that has lost focus ("Document is not focused"), and an await gives it the
 * chance to. If the Clipboard API still refuses, the old copy command in this page does it.
 */
export function copyText(text: string, doc: Document = document): Promise<boolean> {
  try {
    return doc.defaultView!.navigator.clipboard.writeText(text).then(() => true, () => legacyCopy(text, doc));
  } catch {
    return Promise.resolve(legacyCopy(text, doc));
  }
}

/** The copy command on a hidden text box: works in an extension page the person just clicked. */
export function legacyCopy(text: string, doc: Document = document): boolean {
  const box = doc.createElement("textarea");
  box.value = text;
  box.setAttribute("readonly", "");
  box.style.position = "fixed";
  box.style.opacity = "0";
  doc.body.append(box);
  box.select();
  try {
    return doc.execCommand("copy");
  } catch {
    return false;
  } finally {
    box.remove();
  }
}

/** The paste keys on this computer: ⌘V on a Mac, Ctrl+V elsewhere. */
export function pasteKeys(platform: string = navigator.userAgent): string {
  return /Mac|iPhone|iPad/.test(platform) ? "⌘V" : "Ctrl+V";
}

/** Rows whose label or value has every word of the search (any case, any accents). */
export function matches(query: string, ...texts: string[]): boolean {
  const fold = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  const haystack = fold(texts.join(" "));
  return fold(query).split(/\s+/).filter(Boolean).every((word) => haystack.includes(word));
}
