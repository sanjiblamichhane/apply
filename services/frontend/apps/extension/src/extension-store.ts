import type { Store } from "./config";

/** A chrome.storage area as a Store. */
export function extensionStore(area: chrome.storage.StorageArea): Store {
  return {
    get: (key) => area.get(key) as Promise<Record<string, unknown>>,
    set: (items) => area.set(items),
    remove: (key) => area.remove(key),
  };
}
