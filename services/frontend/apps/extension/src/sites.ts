/**
 * Other sites to fill forms on: one the person chooses gets the browser's permission for that origin only (the
 * browser asks them), then the content script, now and on every later visit. Forgetting it takes both away.
 */
const scriptId = (origin: string) => `site:${origin}`;

export function originOf(url: string | undefined): string | null {
  if (!url) return null;
  try {
    const { protocol, origin } = new URL(url);
    return protocol === "https:" || protocol === "http:" ? origin : null;
  } catch {
    return null;
  }
}

/** Ask for the site (from a click: the browser shows its prompt), then put the content script on it. */
export async function allowSite(tabId: number, origin: string): Promise<boolean> {
  const pattern = `${origin}/*`;
  const granted = await chrome.permissions.request({ origins: [pattern] });
  if (!granted) return false;
  const id = scriptId(origin);
  const registered = await chrome.scripting.getRegisteredContentScripts({ ids: [id] });
  if (registered.length === 0) {
    await chrome.scripting.registerContentScripts([
      { id, matches: [pattern], js: ["content.js"], runAt: "document_idle", persistAcrossSessions: true },
    ]);
  }
  await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  return true;
}

export async function forgetSite(origin: string): Promise<void> {
  const id = scriptId(origin);
  if ((await chrome.scripting.getRegisteredContentScripts({ ids: [id] })).length) {
    await chrome.scripting.unregisterContentScripts({ ids: [id] });
  }
  await chrome.permissions.remove({ origins: [`${origin}/*`] });
}

export async function isAllowed(origin: string): Promise<boolean> {
  return (await chrome.scripting.getRegisteredContentScripts({ ids: [scriptId(origin)] })).length > 0;
}
