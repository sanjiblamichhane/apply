/**
 * WCAG 2.2 contrast, computed from the tokens in tokens.css: the test (tests/contrast.test.ts) and the report
 * (scripts/contrast-report.mjs, which writes CONTRAST.md) both use this, so they can't disagree.
 */

/** Token name (without the leading --) to its "h s% l%" triple. */
export type Tokens = { [token: string]: string };

export interface Pair {
  fg: string;
  bg: string;
  min: number;            // 4.5 for text, 3 for UI component boundaries and focus indicators
  use: string;
}

/** The pairs apply's screens actually put together. Add one whenever a component combines two tokens. */
export const PAIRS: Pair[] = [
  { fg: "foreground", bg: "background", min: 4.5, use: "body text" },
  { fg: "card-foreground", bg: "card", min: 4.5, use: "text on cards" },
  { fg: "popover-foreground", bg: "popover", min: 4.5, use: "menus and dialogs" },
  { fg: "foreground", bg: "muted", min: 4.5, use: "text on muted surfaces, muted badges" },
  { fg: "muted-foreground", bg: "background", min: 4.5, use: "secondary text; a scroll bar's thumb" },
  { fg: "muted-foreground", bg: "muted", min: 4.5, use: "secondary text on muted surfaces; a copy value's outline on hover; a switch's knob when off" },
  { fg: "muted-foreground", bg: "card", min: 4.5, use: "secondary text on cards; the sidebar's scroll bar thumb" },
  { fg: "muted-foreground", bg: "popover", min: 4.5, use: "secondary text in menus, dialogs and toasts" },
  { fg: "primary-foreground", bg: "primary", min: 4.5, use: "primary buttons; a switch's knob when on; the chosen theme in the extension's Settings" },
  { fg: "secondary-foreground", bg: "secondary", min: 4.5, use: "secondary buttons" },
  { fg: "accent-foreground", bg: "accent", min: 4.5, use: "highlighted menu items" },
  { fg: "destructive-foreground", bg: "destructive", min: 4.5, use: "destructive buttons" },
  { fg: "success-foreground", bg: "success", min: 4.5, use: "success badges" },
  { fg: "primary", bg: "background", min: 4.5, use: "links; a switch's track when on" },
  { fg: "primary", bg: "card", min: 4.5, use: "links on cards; a switch's track when on (cards)" },
  { fg: "destructive", bg: "background", min: 4.5, use: "error text" },
  { fg: "destructive", bg: "card", min: 4.5, use: "error text on cards" },
  { fg: "success", bg: "background", min: 4.5, use: "success text" },
  { fg: "success", bg: "card", min: 4.5, use: "success text on cards" },
  { fg: "input", bg: "background", min: 3, use: "field borders; a switch's track when off; the extension's theme control" },
  { fg: "input", bg: "card", min: 3, use: "field borders on cards; a switch's track when off (cards)" },
  { fg: "ring", bg: "background", min: 3, use: "focus ring" },
  { fg: "ring", bg: "card", min: 3, use: "focus ring on cards" },
  { fg: "ring", bg: "muted", min: 3, use: "focus ring on muted tiles (the extension's copy values)" },
  { fg: "primary", bg: "muted", min: 3, use: "a copied value's ring and tick (the extension)" },
  { fg: "primary", bg: "popover", min: 3, use: "the chosen profile's tick in the extension's list" },
];

export function parseTokens(css: string, selector: ":root" | ".dark"): Tokens {
  const escaped = selector.replace(".", "\\.");
  const block = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "s").exec(css)?.[1] ?? "";
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*hsl\(([^)]*)\)/g)].map((m) => [m[1]!, m[2]!.trim()]));
}

type Rgb = [number, number, number];

/** "h s% l%" to gamma-encoded sRGB channels in 0..1, via chroma and the sextant the hue falls in. */
function hslToRgb(hsl: string): Rgb {
  const [hue, satPct, lightPct] = hsl.split(/\s+/).map((v) => Number.parseFloat(v)) as Rgb;
  const l = lightPct / 100;
  const chroma = (1 - Math.abs(2 * l - 1)) * (satPct / 100);
  const sextant = (((hue % 360) + 360) % 360) / 60;
  const second = chroma * (1 - Math.abs((sextant % 2) - 1));
  const offset = l - chroma / 2;
  const table: Rgb[] = [
    [chroma, second, 0], [second, chroma, 0], [0, chroma, second],
    [0, second, chroma], [second, 0, chroma], [chroma, 0, second],
  ];
  const [r, g, b] = table[Math.min(5, Math.floor(sextant))]!;
  return [r + offset, g + offset, b + offset];
}

/** WCAG relative luminance: undo the sRGB curve per channel, then weight by the eye's sensitivity. */
const WEIGHTS: Rgb = [0.2126, 0.7152, 0.0722];
function luminance(rgb: Rgb): number {
  const linear = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return rgb.reduce((sum, c, i) => sum + WEIGHTS[i]! * linear(c), 0);
}

export function ratio(fg: string, bg: string): number {
  return ratioRgb(hslToRgb(fg), hslToRgb(bg));
}

function ratioRgb(fg: Rgb, bg: Rgb): number {
  const a = luminance(fg);
  const b = luminance(bg);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

const mix = (a: Rgb, b: Rgb, share: number): Rgb =>
  [0, 1, 2].map((i) => share * a[i]! + (1 - share) * b[i]!) as Rgb;

/*
 * The sign-in pages' glass (theme.css, `glass` and `glass-backdrop`): the card colour at 80% over a backdrop of
 * the theme's colours at up to 35% on the background. A pair passes on glass only if it passes over the
 * strongest point of every one of those colours.
 */
export const GLASS_OPACITY = 0.8;
export const GLASS_BACKDROP: [token: string, strength: number][] = [["primary", 0.35], ["success", 0.3], ["secondary", 0.3]];

export const GLASS_PAIRS: Omit<Pair, "bg">[] = [
  { fg: "foreground", min: 4.5, use: "text on glass" },
  { fg: "muted-foreground", min: 4.5, use: "secondary text on glass; field borders on glass" },
  { fg: "primary", min: 4.5, use: "links on glass" },
  { fg: "destructive", min: 4.5, use: "error text on glass" },
  { fg: "ring", min: 3, use: "focus ring on glass" },
];

/** A colour's worst contrast on the glass, over each backdrop colour at its strongest. */
export function onGlass(tokens: Tokens, fg: string): number {
  const bg = hslToRgb(tokens.background!);
  const card = hslToRgb(tokens.card!);
  return Math.min(...GLASS_BACKDROP.map(([token, strength]) => {
    const under = mix(hslToRgb(tokens[token]!), bg, strength);
    return ratioRgb(hslToRgb(tokens[fg]!), mix(card, under, GLASS_OPACITY));
  }));
}

export function themes(css: string): { light: Tokens; dark: Tokens } {
  const light = parseTokens(css, ":root");
  return { light, dark: { ...light, ...parseTokens(css, ".dark") } };
}
