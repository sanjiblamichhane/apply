/**
 * The offscreen page that clears the clipboard a minute after the copy panel put something on it, if the person
 * asked for that. It clears only what apply copied: if the person copied anything else since, it's left alone.
 * It can't reach the computer's clipboard history (Windows' Win+V, clipboard managers), which keep their copy.
 */
import type { ClipboardMessage } from "./messages";

let pending: ReturnType<typeof setTimeout> | null = null;

const same = (a: string, b: string) => a.replace(/\r\n/g, "\n") === b.replace(/\r\n/g, "\n");

/** What's on the clipboard now: pasted into a box on this page (needs clipboardRead). */
function current(): string {
  const box = document.querySelector("textarea")!;
  box.value = "";
  box.focus();
  document.execCommand("paste");
  return box.value;
}

function clear(): void {
  const empty = (event: ClipboardEvent) => {
    event.clipboardData?.setData("text/plain", "");
    event.preventDefault();
  };
  document.addEventListener("copy", empty);
  try {
    document.execCommand("copy");
  } finally {
    document.removeEventListener("copy", empty);
  }
}

chrome.runtime.onMessage.addListener((message: ClipboardMessage) => {
  if (message.type !== "clear-later") return;
  if (pending) clearTimeout(pending); // a newer copy: its minute counts
  pending = setTimeout(() => {
    pending = null;
    if (same(current(), message.text)) clear();
    const done: ClipboardMessage = { type: "clipboard-done" };
    void chrome.runtime.sendMessage(done).catch(() => undefined);
  }, message.after);
});
