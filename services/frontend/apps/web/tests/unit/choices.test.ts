import { describe, expect, it } from "vitest";

import { DEFAULT_PACK, PACK_STORAGE, readPack, writePack } from "@/lib/pack-choice";
import { readCollapsed, SIDEBAR_STORAGE, writeCollapsed } from "@/lib/sidebar";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v), data };
}
const broken = { getItem: () => { throw new Error("off"); }, setItem: () => { throw new Error("off"); } };

describe("the pack choice", () => {
  it("is remembered, and starts in the default pack", () => {
    const storage = memoryStorage();
    expect(readPack(storage)).toBe(DEFAULT_PACK);
    writePack(storage, "tender");
    expect(storage.data.get(PACK_STORAGE)).toBe("tender");
    expect(readPack(storage)).toBe("tender");
  });

  it("ignores what isn't a pack key, and storage that's turned off", () => {
    expect(readPack(memoryStorage({ [PACK_STORAGE]: "<script>" }))).toBe(DEFAULT_PACK);
    const storage = memoryStorage({ [PACK_STORAGE]: "grant" });
    writePack(storage, "Not A Key!");
    expect(readPack(storage)).toBe("grant");
    expect(readPack(broken)).toBe(DEFAULT_PACK);
    expect(() => writePack(broken, "grant")).not.toThrow();
    expect(readPack(null)).toBe(DEFAULT_PACK);
  });
});

describe("the sidebar", () => {
  it("starts expanded and remembers being collapsed", () => {
    const storage = memoryStorage();
    expect(readCollapsed(storage)).toBe(false);
    writeCollapsed(storage, true);
    expect(storage.data.get(SIDEBAR_STORAGE)).toBe("collapsed");
    expect(readCollapsed(storage)).toBe(true);
    writeCollapsed(storage, false);
    expect(readCollapsed(storage)).toBe(false);
    expect(readCollapsed(broken)).toBe(false);
    expect(() => writeCollapsed(broken, true)).not.toThrow();
  });
});

describe("the language this browser chose", () => {
  it("is read from its cookie, and nothing else counts as a choice", async () => {
    const { readLocaleCookie } = await import("@/lib/locale");
    expect(readLocaleCookie("a=1; apply_locale=ne; b=2")).toBe("ne");
    expect(readLocaleCookie("apply_locale=en")).toBe("en");
    expect(readLocaleCookie("apply_locale=fr")).toBeNull();
    expect(readLocaleCookie("other=ne")).toBeNull();
    expect(readLocaleCookie("")).toBeNull();
  });
});
