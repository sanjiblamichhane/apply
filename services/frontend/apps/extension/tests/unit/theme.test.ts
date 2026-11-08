import { describe, expect, it } from "vitest";

import { isDark, isTheme, THEMES } from "../../src/theme";

describe("the panel's theme", () => {
  it("follows the system unless Light or Dark is chosen", () => {
    expect(isDark("system", true)).toBe(true);
    expect(isDark("system", false)).toBe(false);
    expect(isDark("dark", false)).toBe(true);
    expect(isDark("light", true)).toBe(false);
  });

  it("takes only the three choices from storage", () => {
    expect(THEMES.every(isTheme)).toBe(true);
    for (const junk of [undefined, null, "", "Dark", "auto", 1]) expect(isTheme(junk)).toBe(false);
  });
});
