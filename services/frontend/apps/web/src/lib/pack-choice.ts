"use client";

/**
 * Which pack the screens are working in (Jobs, Tenders, Grants, Contracts): chosen in the sidebar and remembered
 * on this device. Applications, Profiles, Matches, Searches, Sources and Saved answers show and create this pack's.
 */
import { useSyncExternalStore } from "react";

export const DEFAULT_PACK = "job";
export const PACK_STORAGE = "apply.pack";
const CHANGED = "apply:pack";

const PACK_KEY = /^[a-z][a-z0-9_]{0,39}$/;

/** The stored choice, if it's a pack key at all (the switcher checks it's one the API knows). */
export function readPack(storage: Pick<Storage, "getItem"> | null | undefined): string {
  try {
    const stored = storage?.getItem(PACK_STORAGE) ?? "";
    return PACK_KEY.test(stored) ? stored : DEFAULT_PACK;
  } catch {
    return DEFAULT_PACK; // storage turned off: work in the default pack
  }
}

export function writePack(storage: Pick<Storage, "setItem"> | null | undefined, key: string): void {
  if (!PACK_KEY.test(key)) return;
  try {
    storage?.setItem(PACK_STORAGE, key);
  } catch {
    // storage turned off: the choice lasts until the page is reloaded
  }
}

function local(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

let memory: string | null = null;

function subscribe(onChange: () => void): () => void {
  const onStorage = (e: StorageEvent) => {
    if (e.key === PACK_STORAGE) {
      memory = null;
      onChange();
    }
  };
  window.addEventListener(CHANGED, onChange);
  window.addEventListener("storage", onStorage); // another tab chose
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

function snapshot(): string {
  return memory ?? readPack(local());
}

/** The current pack, and a way to choose another. */
export function useCurrentPack(): [string, (key: string) => void] {
  const pack = useSyncExternalStore(subscribe, snapshot, () => DEFAULT_PACK);
  const choose = (key: string) => {
    writePack(local(), key);
    memory = PACK_KEY.test(key) ? key : memory;
    window.dispatchEvent(new Event(CHANGED));
  };
  return [pack, choose];
}
