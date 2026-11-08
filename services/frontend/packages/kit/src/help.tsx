"use client";

/**
 * Help on screen. A HelpButton ("?") next to a heading opens that heading's guide. Where the app has placed a
 * GuideDock and the window is wide (80 rem or more), the guide takes a column of its own and the page gets
 * narrower, so neither covers the other. Anywhere else it slides in as a non-modal sheet from the end edge.
 *
 * Keyboard and focus: opening moves focus to the guide's title; Escape or Close hides it and puts focus back on
 * whatever opened it. Links to other guides swap the guide in place; any other link opens in a new tab.
 */
import { Button, cn, Sheet, SheetContent, SheetDescription, SheetTitle, Tooltip, TooltipContent, TooltipTrigger } from "@apply/ui";
import { Book, Help, X } from "@apply/ui/icons";
import {
  type AnchorHTMLAttributes,
  type ComponentType,
  createContext,
  type MouseEvent,
  type ReactNode,
  type RefObject,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";

import { type GuideLibrary, guideSlugFromHref, type HelpGuide, pickTranslation } from "./guides";

/** The app's Markdown component. The help panel hands it its own link component. */
export type MarkdownComponent = ComponentType<{
  children: string;
  components?: { a?: ComponentType<AnchorHTMLAttributes<HTMLAnchorElement>> };
}>;

/** Words the help UI needs, in the reader's language. */
export interface HelpLabels {
  /** Read out as the panel's description, e.g. "Help". */
  panel: string;
  /** The accessible name and tooltip of a "?" button, given its guide's title, e.g. "Help: Sources". */
  help: (title: string) => string;
  /** The docked panel's close button. */
  close: string;
}

type ShownGuide = HelpGuide & { language: string; slug: string };

interface HelpState {
  library: GuideLibrary;
  locale: string;
  shown: ShownGuide | null;
  docked: boolean;
  labels: HelpLabels;
  titleRef: RefObject<HTMLHeadingElement | null>;
  content: ReactNode;
  show: (slug: string) => void;
  hide: () => void;
  setDockMounted: (mounted: boolean) => void;
}

const HelpContext = createContext<HelpState | null>(null);

const WIDE_ENOUGH_TO_DOCK = "(min-width: 80rem)";
const PROSE = cn(
  "min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain px-5 py-4 text-sm leading-relaxed [&:lang(ne)]:leading-loose",
  "[&_a]:text-primary [&_a]:underline [&_strong]:font-semibold [&_h3]:pt-2 [&_h3]:text-base [&_h3]:font-semibold",
  "[&_li]:ms-5 [&_ul]:list-disc [&_ul]:space-y-1 [&_ol]:list-decimal [&_ol]:space-y-2",
);

function subscribeToWidth(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const query = window.matchMedia(WIDE_ENOUGH_TO_DOCK);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function isWideNow(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(WIDE_ENOUGH_TO_DOCK).matches;
}

/** Holds which guide is open and draws it, as a sheet or (with a GuideDock on a wide screen) docked. */
export function HelpProvider({ library, locale, Markdown, labels, children }: {
  library: GuideLibrary;
  locale: string;
  Markdown: MarkdownComponent;
  labels: HelpLabels;
  children: ReactNode;
}) {
  const [slug, setSlug] = useState<string | null>(null);
  const [dockMounted, setDockMounted] = useState(false);
  const wide = useSyncExternalStore(subscribeToWidth, isWideNow, () => false);
  const docked = dockMounted && wide;
  const returnFocusTo = useRef<HTMLElement | null>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);

  const shown = useMemo<ShownGuide | null>(() => {
    const picked = slug ? pickTranslation(library[slug], locale) : null;
    return picked && slug ? { ...picked, slug } : null;
  }, [library, locale, slug]);

  const show = useCallback((next: string) => {
    if (!pickTranslation(library[next], locale)) return;
    // Only the first guide opened records where to return; moving between guides keeps that.
    if (slug === null && document.activeElement instanceof HTMLElement) returnFocusTo.current = document.activeElement;
    setSlug(next);
  }, [library, locale, slug]);

  const hide = useCallback(() => {
    setSlug(null);
    returnFocusTo.current?.focus();
    returnFocusTo.current = null;
  }, []);

  // Each time a guide appears, or moves between the sheet and the dock, put focus on its title.
  const shownSlug = shown?.slug;
  useEffect(() => {
    if (shownSlug) titleRef.current?.focus();
  }, [shownSlug, docked]);

  const GuideAnchor = useMemo(() => function GuideAnchor({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement>) {
    const target = guideSlugFromHref(href);
    if (target && library[target]) {
      const follow = (event: MouseEvent<HTMLAnchorElement>) => {
        event.preventDefault();
        show(target);
      };
      return <a {...rest} href={`#help-${target}`} onClick={follow}>{children}</a>;
    }
    return <a {...rest} href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
  }, [library, show]);

  const content = useMemo(() => (shown ? (
    <div lang={shown.language} data-testid="guide-body" className={PROSE}>
      <Markdown components={{ a: GuideAnchor }}>{shown.markdown}</Markdown>
    </div>
  ) : null), [shown, Markdown, GuideAnchor]);

  const state = useMemo<HelpState>(() => ({
    library, locale, shown, docked, labels, titleRef, content, show, hide, setDockMounted,
  }), [library, locale, shown, docked, labels, content, show, hide]);

  return (
    <HelpContext.Provider value={state}>
      {children}
      <Sheet open={shown !== null && !docked} modal={false} onOpenChange={(open) => { if (!open) hide(); }}>
        <SheetContent side="end" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm"
          onOpenAutoFocus={(event) => { event.preventDefault(); titleRef.current?.focus(); }}
          onCloseAutoFocus={(event) => event.preventDefault()}
          onInteractOutside={(event) => event.preventDefault()}>
          {shown && !docked ? (
            <>
              <GuideHeader guide={shown} titleRef={titleRef} inSheet />
              <SheetDescription className="sr-only">{labels.panel}</SheetDescription>
              {content}
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </HelpContext.Provider>
  );
}

function GuideHeader({ guide, titleRef, titleId, inSheet = false, action }: {
  guide: ShownGuide;
  titleRef: RefObject<HTMLHeadingElement | null>;
  titleId?: string;
  inSheet?: boolean;
  action?: ReactNode;
}) {
  const heading = (
    // id only when docked: in the sheet, the title's id comes from the sheet (an undefined id here would erase it).
    <h2 ref={titleRef} {...(titleId ? { id: titleId } : {})} tabIndex={-1} lang={guide.language}
      className="min-w-0 flex-1 text-lg font-semibold outline-none focus-visible:outline-2 focus-visible:outline-ring">
      {guide.title}
    </h2>
  );
  return (
    // The sheet draws its own close button in the corner, so leave room for it there.
    <header className={cn("flex items-center gap-2 border-b px-5 py-4", action ? "pe-2" : "pe-14")}>
      <Book className="size-5 shrink-0 text-primary" aria-hidden />
      {inSheet ? <SheetTitle asChild>{heading}</SheetTitle> : heading}
      {action}
    </header>
  );
}

/**
 * The column an open guide docks into on a wide screen. Put one in the app's layout, after the page; while it's
 * mounted, wide screens dock instead of using the sheet. It renders nothing while no guide is docked.
 */
export function GuideDock({ className }: { className?: string }) {
  const help = useContext(HelpContext);
  const titleId = useId();
  const descriptionId = useId();
  const setDockMounted = help?.setDockMounted;
  useEffect(() => {
    if (!setDockMounted) return;
    setDockMounted(true);
    return () => setDockMounted(false);
  }, [setDockMounted]);

  // Escape anywhere inside the docked guide closes it, as it does the sheet. The listener goes on the element
  // itself because a landmark isn't something to give a React key handler to.
  const region = useRef<HTMLElement>(null);
  const isDocked = Boolean(help?.docked && help.shown);
  const hide = help?.hide;
  useEffect(() => {
    const element = region.current;
    if (!isDocked || !element || !hide) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.stopPropagation();
      hide();
    };
    element.addEventListener("keydown", onKeyDown);
    return () => element.removeEventListener("keydown", onKeyDown);
  }, [isDocked, hide]);

  if (!help?.docked || !help.shown || !hide) return null;
  const { shown, labels, titleRef, content } = help;
  return (
    <aside ref={region} aria-labelledby={titleId} aria-describedby={descriptionId}
      className={cn("flex h-full w-[22rem] shrink-0 flex-col border-s bg-card", className)}>
      <p id={descriptionId} className="sr-only">{labels.panel}</p>
      <GuideHeader guide={shown} titleRef={titleRef} titleId={titleId} action={
        <Button type="button" variant="ghost" size="icon" aria-label={labels.close} title={labels.close} onClick={hide}>
          <X aria-hidden />
        </Button>
      } />
      {content}
    </aside>
  );
}

/** What the help system offers to the rest of the app, or null outside a HelpProvider. */
export function useHelp(): { show: (slug: string) => void; titleOf: (slug: string) => string | null } | null {
  const help = useContext(HelpContext);
  return useMemo(() => help && {
    show: help.show,
    titleOf: (slug: string) => pickTranslation(help.library[slug], help.locale)?.title ?? null,
  }, [help]);
}

/**
 * The "?" that opens a guide. It draws nothing when there's no guide for `slug` (or no HelpProvider), since a
 * button that does nothing is worse than no button. Its name and tooltip come from the guide's title; the hit
 * area is 44 px square around a smaller icon.
 */
export function HelpButton({ slug, labels, className }: { slug: string; labels: Pick<HelpLabels, "help">; className?: string }) {
  const help = useHelp();
  const title = help?.titleOf(slug);
  if (!help || title == null) return null;
  const name = labels.help(title);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button type="button" variant="ghost" size="icon" aria-label={name} data-help={slug}
          className={cn("shrink-0 rounded-full text-muted-foreground hover:text-primary", className)}
          onClick={() => help.show(slug)}>
          <Help className="size-5" aria-hidden />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top">{name}</TooltipContent>
    </Tooltip>
  );
}
