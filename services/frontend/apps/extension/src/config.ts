/**
 * The connection to apply, kept in chrome.storage.local on this computer (never synced, so the token
 * doesn't travel to other browsers signed in to the same account).
 */
import type { Locale } from "@apply/i18n";

export interface Connection {
  apiUrl: string;
  token: string;
  email: string;
  locale: Locale;
  webUrl: string | null;
}

export interface Store {
  get(key: string): Promise<Record<string, unknown>>;
  set(items: Record<string, unknown>): Promise<void>;
  remove(key: string): Promise<void>;
}

export const DEFAULT_API = __DEFAULT_API__;

export function cleanApiUrl(value: string): string | null {
  try {
    const url = new URL(value.trim());
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.origin;
  } catch {
    return null;
  }
}

/** True for the API addresses the manifest already allows; any other needs the browser's permission first. */
export function isBuiltInApi(origin: string): boolean {
  return ["http://127.0.0.1:8110", "http://localhost:8110", DEFAULT_API].includes(origin);
}

export async function loadConnection(store: Store): Promise<Connection | null> {
  const found = (await store.get("connection")).connection as Connection | undefined;
  return found && found.apiUrl && found.token ? found : null;
}

export async function saveConnection(store: Store, connection: Connection): Promise<void> {
  await store.set({ connection });
}

export async function forget(store: Store): Promise<void> {
  await store.remove("connection");
}

export async function localeOverride(store: Store): Promise<Locale | null> {
  const value = (await store.get("locale")).locale;
  return value === "en" || value === "ne" ? value : null;
}
