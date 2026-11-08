"use client";

/** Whether the wide-screen sidebar is collapsed to icons: the person's choice, remembered on this device. */
import { useSyncExternalStore } from "react";

export const SIDEBAR_STORAGE = "apply.sidebar";

export function readCollapsed(storage: Pick<Storage, "getItem"> | null | undefined): boolean {
  try {
    return storage?.getItem(SIDEBAR_STORAGE) === "collapsed";
  } catch {
    return false;
  }
}

export function writeCollapsed(storage: Pick<Storage, "setItem"> | null | undefined, collapsed: boolean): void {
  try {
    storage?.setItem(SIDEBAR_STORAGE, collapsed ? "collapsed" : "expanded");
  } catch {
    // storage turned off: the choice lasts until the page is reloaded
  }
}

// One small store for the tab: listeners hear this tab's changes directly, and other tabs' through "storage".
const listeners = new Set<() => void>();
let chosen: boolean | null = null;

function subscribe(listener: () => void): () => void {
  const fromOtherTab = (event: StorageEvent) => {
    if (event.key !== SIDEBAR_STORAGE) return;
    chosen = null;
    listener();
  };
  listeners.add(listener);
  window.addEventListener("storage", fromOtherTab);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", fromOtherTab);
  };
}

function current(): boolean {
  if (chosen !== null) return chosen;
  return readCollapsed(typeof window === "undefined" ? null : window.localStorage);
}

function choose(collapsed: boolean): void {
  chosen = collapsed;
  writeCollapsed(window.localStorage, collapsed);
  listeners.forEach((listener) => listener());
}

export function useSidebarCollapsed(): [boolean, (collapsed: boolean) => void] {
  return [useSyncExternalStore(subscribe, current, () => false), choose];
}
