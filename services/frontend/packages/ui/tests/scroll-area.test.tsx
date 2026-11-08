import { readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ScrollArea, ScrollBar } from "../src";
import { ratio, themes } from "../src/lib/contrast";

/** The first paint, as the server sends it: enough to see what each element is and what it carries. */
const paint = (node: React.ReactNode) => renderToStaticMarkup(<>{node}</>);

/** The opening tag of the element with this data-slot. */
function tag(markup: string, slot: string): string {
  const found = new RegExp(`<[a-z]+[^>]*data-slot="${slot}"[^>]*>`).exec(markup);
  expect(found, `no ${slot} in ${markup}`).not.toBeNull();
  return found![0];
}

describe("ScrollArea", () => {
  it("puts its content inside the element that scrolls", () => {
    const markup = paint(<ScrollArea className="h-40"><p>First line</p></ScrollArea>);
    expect(tag(markup, "scroll-area")).toContain("h-40");
    const viewport = markup.indexOf('data-slot="scroll-area-viewport"');
    expect(viewport).toBeGreaterThan(-1);
    expect(markup.indexOf("First line")).toBeGreaterThan(viewport);
  });

  it("lays content out at its own width, so text wraps instead of running off the side", () => {
    // Radix wraps the content in a `display: table` box, which grows to its widest line; this overrides it.
    expect(tag(paint(<ScrollArea>text</ScrollArea>), "scroll-area-viewport")).toContain("[&amp;&gt;div]:block!");
  });

  it("stays out of the tab order and unnamed unless it is given a label", () => {
    const viewport = tag(paint(<ScrollArea>text</ScrollArea>), "scroll-area-viewport");
    expect(viewport).not.toContain("tabindex");
    expect(viewport).not.toContain("role=");
    expect(viewport).not.toContain("aria-label");
  });

  it("with a label, is a named region the keyboard can reach and scroll (WCAG 2.1.1)", () => {
    const viewport = tag(paint(<ScrollArea label="Version 2">text</ScrollArea>), "scroll-area-viewport");
    expect(viewport).toContain('role="region"');
    expect(viewport).toContain('aria-label="Version 2"');
    expect(viewport).toContain('tabindex="0"');
    // Focus shows on the scrolling element itself, inside its edge so a rounded parent can't clip it.
    expect(viewport).toContain("focus-visible:outline-ring");
    expect(viewport).toContain("focus-visible:-outline-offset-2");
  });

  it("adds the caller's classes to the scrolling element, not the frame around it", () => {
    const markup = paint(<ScrollArea className="border" viewportClassName="max-h-60 overscroll-contain">text</ScrollArea>);
    expect(tag(markup, "scroll-area-viewport")).toContain("max-h-60 overscroll-contain");
    expect(tag(markup, "scroll-area")).not.toContain("max-h-60");
  });

  it("hands the scrolling element to a ref", () => {
    // Refs attach on the client; on the server the callback is never called, so this checks the prop is
    // accepted and doesn't leak into the markup as an attribute.
    const markup = paint(<ScrollArea viewportRef={() => undefined}>text</ScrollArea>);
    expect(markup).not.toContain("viewportref");
  });

  it("always has a vertical bar, and a horizontal one when asked", () => {
    const tall = paint(<ScrollArea type="always">text</ScrollArea>);
    expect(tag(tall, "scroll-area-scrollbar")).toContain('data-orientation="vertical"');

    const wide = paint(<ScrollArea type="always"><table /><ScrollBar orientation="horizontal" /></ScrollArea>);
    const bars = [...wide.matchAll(/data-slot="scroll-area-scrollbar"[^>]*data-orientation="(\w+)"|data-orientation="(\w+)"[^>]*data-slot="scroll-area-scrollbar"/g)]
      .map((m) => m[1] ?? m[2]);
    expect(bars.sort()).toEqual(["horizontal", "vertical"]);
  });

  it("keeps the bar's spacer on the reading direction's side", () => {
    const bar = tag(paint(<ScrollArea type="always">text</ScrollArea>), "scroll-area-scrollbar");
    expect(bar).toContain("border-s");
    expect(bar).not.toMatch(/\bborder-l\b/);
  });
});

describe("the scroll bar's thumb", () => {
  // Radix only draws the thumb once it has measured the content, which a server render never does, so the
  // colour is read from the component's source and checked against every surface a scroll area sits on.
  const source = readFileSync(new URL("../src/components/scroll-area.tsx", import.meta.url), "utf-8");
  const thumb = /<ScrollAreaPrimitive\.ScrollAreaThumb[\s\S]*?className="([^"]*)"/.exec(source)?.[1] ?? "";
  const token = /\bbg-([a-z-]+)(?![\w/-])/.exec(thumb)?.[1];
  const tokens = themes(readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf-8"));

  it("is painted with one solid theme colour", () => {
    expect(token, thumb).toBeDefined();
    expect(thumb, "a translucent thumb can't be checked for contrast").not.toMatch(/\bbg-[a-z-]+\/\d+/);
  });

  for (const theme of ["light", "dark"] as const) {
    for (const surface of ["background", "card", "popover", "muted"]) {
      it(`stands out 3:1 from ${surface} in the ${theme} theme (WCAG 1.4.11)`, () => {
        const colours = tokens[theme];
        expect(ratio(colours[token!]!, colours[surface]!)).toBeGreaterThanOrEqual(3);
      });
    }
  }
});
