import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { GLASS_PAIRS, onGlass, PAIRS, ratio, themes } from "../src/lib/contrast";

const css = readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf-8");
const { light, dark } = themes(css);

describe("WCAG 2.2 AA contrast of every token pair", () => {
  for (const [name, tokens] of [["light", light], ["dark", dark]] as const) {
    for (const pair of PAIRS) {
      it(`${name}: ${pair.fg} on ${pair.bg} (${pair.use}) ≥ ${pair.min}:1`, () => {
        expect(tokens[pair.fg], `${pair.fg} is not defined`).toBeDefined();
        expect(tokens[pair.bg], `${pair.bg} is not defined`).toBeDefined();
        expect(ratio(tokens[pair.fg]!, tokens[pair.bg]!)).toBeGreaterThanOrEqual(pair.min);
      });
    }
  }

  for (const [name, tokens] of [["light", light], ["dark", dark]] as const) {
    for (const pair of GLASS_PAIRS) {
      it(`${name}: ${pair.fg} on glass, over its backdrop's strongest colour (${pair.use}) ≥ ${pair.min}:1`, () => {
        expect(onGlass(tokens, pair.fg)).toBeGreaterThanOrEqual(pair.min);
      });
    }
  }

  it("the maths agrees with a known value (black on white is 21:1)", () => {
    expect(ratio("0 0% 0%", "0 0% 100%")).toBeCloseTo(21, 5);
  });
});
