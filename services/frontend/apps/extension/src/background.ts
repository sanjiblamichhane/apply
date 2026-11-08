/**
 * The service worker: opens the side panel from the toolbar button, records a submission when a filled form's
 * thank-you page appears (src/recorder.ts) and tells the panel, and, if the person asked for it, clears what
 * the copy panel copied a minute later (through the offscreen page: src/offscreen.ts).
 */
import { ExtensionApi } from "./api";
import { extensionStore } from "./extension-store";
import { loadConnection } from "./config";
import { type Broadcast, CLEAR_CLIPBOARD, CLIPBOARD_PERMISSIONS, type ClipboardMessage, type ToBackground } from "./messages";
import { makeRecorder } from "./recorder";

const local = extensionStore(chrome.storage.local);
const session = extensionStore(chrome.storage.session);

void chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

const record = makeRecorder(session, async () => {
  const connection = await loadConnection(local);
  return connection ? new ExtensionApi(connection.apiUrl, connection.token) : null;
});

async function clearLater(text: string): Promise<void> {
  if (!(await local.get(CLEAR_CLIPBOARD))[CLEAR_CLIPBOARD]) return;
  if (!(await chrome.permissions.contains({ permissions: CLIPBOARD_PERMISSIONS }))) return;
  if (!(await chrome.offscreen.hasDocument())) {
    await chrome.offscreen.createDocument({
      url: "offscreen.html",
      reasons: [chrome.offscreen.Reason.CLIPBOARD],
      justification: "Clear what apply copied, a minute later, as the person asked",
    }).catch(() => undefined); // made already by a copy a moment ago
  }
  const message: ClipboardMessage = { type: "clear-later", text, after: __CLEAR_AFTER_MS__ };
  await chrome.runtime.sendMessage(message).catch(() => undefined);
}

chrome.runtime.onMessage.addListener((message: ToBackground | ClipboardMessage, sender) => {
  if (message.type === "copied") { void clearLater(message.text); return; }
  if (message.type === "clipboard-done") { void chrome.offscreen.closeDocument().catch(() => undefined); return; }
  const tabId = sender.tab?.id;
  if (message.type !== "confirmed" || tabId === undefined) return;
  void record(tabId, message.url).then((recorded) => {
    if (!recorded) return;
    const note: Broadcast = { type: "recorded", tabId };
    chrome.runtime.sendMessage(note).catch(() => undefined); // the panel may be closed
  });
});
