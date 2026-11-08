// Writes CONTRAST.md: every token pair apply uses, with its ratio in light and dark.
//   pnpm --filter @apply/ui contrast
import { readFileSync, writeFileSync } from "node:fs";

const { GLASS_PAIRS, onGlass, PAIRS, ratio, themes } = await import("../src/lib/contrast.ts");

const css = readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf-8");
const { light, dark } = themes(css);
const rows = PAIRS.map((p) => {
  const l = ratio(light[p.fg], light[p.bg]);
  const d = ratio(dark[p.fg], dark[p.bg]);
  const ok = (r) => (r >= p.min ? "pass" : "**FAIL**");
  return `| ${p.use} | \`${p.fg}\` on \`${p.bg}\` | ${p.min}:1 | ${l.toFixed(2)}:1 ${ok(l)} | ${d.toFixed(2)}:1 ${ok(d)} |`;
});
rows.push(...GLASS_PAIRS.map((p) => {
  const l = onGlass(light, p.fg);
  const d = onGlass(dark, p.fg);
  const ok = (r) => (r >= p.min ? "pass" : "**FAIL**");
  return `| ${p.use} | \`${p.fg}\` on glass (worst point) | ${p.min}:1 | ${l.toFixed(2)}:1 ${ok(l)} | ${d.toFixed(2)}:1 ${ok(d)} |`;
}));
writeFileSync(new URL("../CONTRAST.md", import.meta.url), [
  "# Contrast (WCAG 2.2 AA)",
  "",
  "Computed from `src/styles/tokens.css` by `scripts/contrast-report.mjs`; `tests/contrast.test.ts` fails below",
  "the minimum. Text needs 4.5:1; component boundaries and focus indicators 3:1. Nothing is conveyed by colour",
  "alone: every state also has text or an icon.",
  "",
  "| Used for | Pair | Minimum | Light | Dark |",
  "|---|---|---|---|---|",
  ...rows,
  "",
].join("\n"));
console.log(rows.join("\n"));
