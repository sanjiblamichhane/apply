import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { TooltipProvider } from "@apply/ui";
import type { AnchorHTMLAttributes, ComponentType } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  checkGuides,
  describeIssue,
  GuideDock,
  guideSlugFromHref,
  HelpButton,
  HelpProvider,
  loadGuides,
  mergeGuides,
  parseGuide,
  pickTranslation,
} from "../src";

afterEach(cleanup);

describe("reading guide files", () => {
  it("takes the title from the front matter and finds links to other guides", () => {
    const guide = parseGuide("---\ntitle: \"Sources\"\n---\n\nSee [Searches](../searches/), [Kit](../kit/en.md) and [the web](https://example.com).\n");
    expect(guide).toEqual({
      title: "Sources",
      markdown: "See [Searches](../searches/), [Kit](../kit/en.md) and [the web](https://example.com).",
      links: ["searches", "kit"],
      strayLinks: [],
    });
    expect(parseGuide("Just text").title).toBe("");
  });

  it("knows which links are guides", () => {
    expect(guideSlugFromHref("../auto/")).toBe("auto");
    expect(guideSlugFromHref("../auto")).toBe("auto");
    expect(guideSlugFromHref("../auto/ne.md")).toBe("auto");
    expect(guideSlugFromHref("https://example.com/auto/")).toBeNull();
    expect(guideSlugFromHref("./notes.md")).toBeNull();
    expect(guideSlugFromHref(undefined)).toBeNull();
  });

  it("groups files by folder and language, and rejects other shapes", () => {
    const library = loadGuides({ "./guides/today/en.md": "---\ntitle: Today\n---\nHi", "./guides/today/ne.md": "---\ntitle: आज\n---\nनमस्ते" });
    expect(Object.keys(library)).toEqual(["today"]);
    expect(library.today?.ne?.title).toBe("आज");
    expect(() => loadGuides({ "./guides/today.en.md": "x" })).toThrow(/<guide>\/<language>\.md/);
  });

  it("falls back to English, and says which language it gave", () => {
    const library = mergeGuides(loadGuides({ "today/en.md": "---\ntitle: Today\n---\nHi" }), loadGuides({ "sources/ne.md": "---\ntitle: स्रोत\n---\nx" }));
    expect(pickTranslation(library.today, "ne")).toMatchObject({ title: "Today", language: "en" });
    expect(pickTranslation(library.sources, "ne")).toMatchObject({ language: "ne" });
    expect(pickTranslation(library.missing, "en")).toBeNull();
  });
});

describe("checking guides", () => {
  it("reports missing translations, titles and text, broken links, and help buttons with no guide", () => {
    const library = loadGuides({
      "today/en.md": "---\ntitle: Today\n---\nSee [x](../gone/) and [y](./notes.md).",
      "today/ne.md": "---\ntitle: आज\n---\nनमस्ते",
      "sources/en.md": "No front matter",
      "blank/en.md": "---\ntitle: Blank\n---\n",
      "blank/ne.md": "---\ntitle: खाली\n---\nx",
    });
    const issues = checkGuides(library, { languages: ["en", "ne"], expected: ["today", "matches"] });
    expect(issues.map(describeIssue)).toEqual([
      "blank/en.md has no text",
      "sources/ne.md is missing",
      "sources/en.md has no title in its front matter",
      "today/en.md links to ./notes.md, which is not a guide",
      "today/en.md links to ../gone/, which is not a guide",
      'nothing in guides/ for "matches"',
    ]);
    expect(checkGuides(loadGuides({ "a/en.md": "---\ntitle: A\n---\nx" }), { languages: ["en"] })).toEqual([]);
  });
});

const LIBRARY = loadGuides({
  "today/en.md": "---\ntitle: Today\n---\nWhat's new. See [Sources](../sources/).",
  "today/ne.md": "---\ntitle: आज\n---\nके नयाँ छ।",
  "sources/en.md": "---\ntitle: Sources\n---\nWhere listings come from. More at [the site](https://example.com).",
});

// A stand-in for the app's Markdown: draws every [text](href) as a link through the component it's given.
function FakeMarkdown({ children, components }: { children: string; components?: { a?: ComponentType<AnchorHTMLAttributes<HTMLAnchorElement>> } }) {
  const A = components?.a ?? "a";
  const parts = children.split(/(\[[^\]]+\]\([^)]+\))/);
  return <p>{parts.map((part, i) => {
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(part);
    return link ? <A key={i} href={link[2]}>{link[1]}</A> : part;
  })}</p>;
}

const LABELS = { panel: "Help", help: (title: string) => `Help: ${title}`, close: "Close" };

function App({ locale = "en", dock = false }: { locale?: string; dock?: boolean }) {
  return (
    <TooltipProvider>
      <HelpProvider library={LIBRARY} locale={locale} Markdown={FakeMarkdown} labels={LABELS}>
        <main><h1>Today</h1></main>
        {dock ? <GuideDock /> : null}
        <HelpButton slug="today" labels={LABELS} />
        <HelpButton slug="not-written" labels={LABELS} />
      </HelpProvider>
    </TooltipProvider>
  );
}

function pretendWide() {
  const matchMedia = vi.fn((query: string) => ({
    matches: query === "(min-width: 80rem)", media: query, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {},
    dispatchEvent: () => false,
  }));
  Object.defineProperty(window, "matchMedia", { value: matchMedia, configurable: true, writable: true });
  return () => Reflect.deleteProperty(window, "matchMedia");
}

describe("the help button and panel", () => {
  it("opens as a sheet, follows guide links in place, sends other links to a new tab, and returns focus", async () => {
    render(<App />);
    expect(screen.getAllByRole("button", { name: /^Help:/ })).toHaveLength(1);
    const button = screen.getByRole("button", { name: "Help: Today" });
    button.focus();
    fireEvent.click(button);
    const title = await screen.findByRole("heading", { name: "Today", level: 2 });
    expect(document.activeElement).toBe(title);

    fireEvent.click(screen.getByRole("link", { name: "Sources" }));
    expect(await screen.findByRole("heading", { name: "Sources", level: 2 })).toBeTruthy();
    const outside = screen.getByRole("link", { name: "the site" });
    expect(outside.getAttribute("target")).toBe("_blank");
    expect(outside.getAttribute("rel")).toBe("noopener noreferrer");

    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
    expect(document.activeElement).toBe(button);
  });

  it("docks on a wide screen as a named region, closed by Close or Escape", async () => {
    const restore = pretendWide();
    try {
      render(<App dock />);
      const button = screen.getByRole("button", { name: "Help: Today" });
      button.focus();
      fireEvent.click(button);
      await screen.findByRole("complementary", { name: "Today" });
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Today", level: 2 }));
      fireEvent.click(screen.getByRole("button", { name: "Close" }));
      expect(screen.queryByRole("complementary")).toBeNull();
      expect(document.activeElement).toBe(button);

      fireEvent.click(button);
      await screen.findByRole("complementary", { name: "Today" });
      fireEvent.keyDown(document.activeElement!, { key: "Escape" });
      expect(screen.queryByRole("complementary")).toBeNull();
      expect(document.activeElement).toBe(button);
    } finally {
      restore();
    }
  });

  it("shows the reader's language, marked with lang", async () => {
    render(<App locale="ne" />);
    fireEvent.click(screen.getByRole("button", { name: "Help: आज" }));
    const title = await screen.findByRole("heading", { name: "आज", level: 2 });
    expect(title.getAttribute("lang")).toBe("ne");
  });
});
