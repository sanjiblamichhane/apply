/**
 * Recording a submission when the board's thank-you page appears: once per filled form, even if the page
 * is reloaded or noticed twice. It runs in the service worker, so it works with the panel closed.
 */
import type { ExtensionApi } from "./api";
import type { Store } from "./config";
import { pendingKey, recordedKey, type PendingFill, type Recorded } from "./messages";

const STALE = 6 * 60 * 60 * 1000; // a form filled this long ago isn't the one being thanked for

export function makeRecorder(session: Store, api: () => Promise<ExtensionApi | null>, now: () => number = Date.now) {
  const busy = new Set<number>();

  return async function record(tabId: number, url: string): Promise<Recorded | null> {
    if (busy.has(tabId)) return null;
    busy.add(tabId);
    try {
      const pending = (await session.get(pendingKey(tabId)))[pendingKey(tabId)] as PendingFill | undefined;
      if (!pending || now() - pending.at > STALE) return null;
      const client = await api();
      if (!client) return null;
      let recorded: Recorded;
      try {
        const submission = await client.submit(pending.applicationId, { confirmation_url: url, filled: pending.filled });
        const application = await client.application(pending.applicationId);
        recorded = { applicationId: pending.applicationId, submissionId: submission.id, stageCode: application.stage.code, at: now() };
      } catch (error) {
        recorded = { applicationId: pending.applicationId, error: (error as { code?: string }).code ?? "INTERNAL", at: now() };
      }
      await session.set({ [recordedKey(tabId)]: recorded });
      if (!recorded.error) await session.remove(pendingKey(tabId));
      return recorded;
    } finally {
      busy.delete(tabId);
    }
  };
}
