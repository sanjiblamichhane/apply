// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";

import { copyText, legacyCopy, matches, pasteKeys } from "../../src/clipboard";

describe("copying", () => {
  it("writes with the Clipboard API, in the click", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(window.navigator, "clipboard", { value: { writeText }, configurable: true });
    await expect(copyText("sam@example.com")).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith("sam@example.com");
  });

  it("falls back to the copy command when the Clipboard API refuses", async () => {
    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText: () => Promise.reject(new DOMException("Document is not focused", "NotAllowedError")) },
      configurable: true,
    });
    document.execCommand = vi.fn(() => true);
    await expect(copyText("Sam")).resolves.toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull(); // the box is gone again
  });

  it("says when nothing could copy", () => {
    document.execCommand = vi.fn(() => false);
    expect(legacyCopy("x")).toBe(false);
  });

  it("names the paste keys of this computer", () => {
    expect(pasteKeys("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0)")).toBe("⌘V");
    expect(pasteKeys("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")).toBe("Ctrl+V");
    expect(pasteKeys("Mozilla/5.0 (X11; Linux x86_64)")).toBe("Ctrl+V");
  });
});

describe("searching the profile", () => {
  it("finds every word, in any case and without accents", () => {
    expect(matches("post code", "Postcode or ZIP", "44600")).toBe(true);
    expect(matches("zip city", "Postcode or ZIP", "44600")).toBe(false); // every word, not any
    expect(matches("himal from", "From", "Jan 2021", "Backend Engineer, Himal Tech")).toBe(true);
    expect(matches("telefono", "Teléfono", "+977 980")).toBe(true);
    expect(matches("", "anything")).toBe(true);
  });
});
