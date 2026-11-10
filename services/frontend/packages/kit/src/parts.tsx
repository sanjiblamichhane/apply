"use client";

import { Button, cn, ScrollArea } from "@apply/ui";
import { Search, WarningAlt } from "@apply/ui/icons";
import { type ComponentType, type InputHTMLAttributes, type ReactNode, useId } from "react";

/** Text for screen readers only. */
export function VisuallyHidden({ children }: { children: ReactNode }) {
  return <span className="sr-only">{children}</span>;
}

/**
 * A page's title, what it's for, and its actions: the page's h1, or an h2 when it shares the screen with a
 * detail that holds the h1 (a split view).
 */
export function PageHeader({ title, description, actions, help, className, level = 1 }: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** The page's "?" (a HelpButton), beside the title. */
  help?: ReactNode;
  className?: string;
  level?: 1 | 2;
}) {
  const Heading = level === 1 ? "h1" : "h2";
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-4", className)}>
      <div className="min-w-0 space-y-1">
        <div className="flex items-center gap-1">
          <Heading className="text-2xl font-semibold tracking-tight">{title}</Heading>
          {help}
        </div>
        {description ? <p className="max-w-prose text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** Nothing here yet: what this place is for, and the one thing to do next. */
export function EmptyState({ icon: Icon, title, body, action, className }: {
  icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  title: ReactNode;
  body?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-3 rounded-xl border border-dashed border-input px-6 py-12 text-center", className)}>
      {Icon ? <Icon className="size-8 text-muted-foreground" aria-hidden /> : null}
      <h2 className="text-lg font-semibold">{title}</h2>
      {body ? <p className="max-w-prose text-sm text-muted-foreground">{body}</p> : null}
      {action}
    </div>
  );
}

/** Something didn't load or didn't work: said in words, with a way to try again. */
export function ErrorNotice({ message, retryLabel, onRetry, className }: {
  message: ReactNode;
  retryLabel?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div role="alert" className={cn("flex flex-wrap items-center gap-3 rounded-lg border border-destructive/60 bg-card px-4 py-3 text-sm", className)}>
      <WarningAlt className="size-5 shrink-0 text-destructive" aria-hidden />
      <p className="min-w-0 flex-1 text-destructive">{message}</p>
      {onRetry && retryLabel ? <Button variant="outline" size="sm" onClick={onRetry}>{retryLabel}</Button> : null}
    </div>
  );
}

/** A search field with a real (visually hidden) label: one per scope (plan §10). */
export function SearchField({ label, className, ...props }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div className={cn("relative", className)}>
      <label htmlFor={id} className="sr-only">{label}</label>
      <Search className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
      <input
        id={id}
        type="search"
        className="flex min-h-11 w-full rounded-md border border-input bg-background py-2 ps-9 pe-3 text-base placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring md:text-sm"
        {...props}
      />
    </div>
  );
}

export interface ViewOption<V extends string> {
  value: V;
  label: string;
  icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
}

/** Board or list: a segmented control. Each option is a toggle button that says which one is on. */
export function ViewSwitcher<V extends string>({ label, options, value, onChange }: {
  label: string;
  options: ViewOption<V>[];
  value: V;
  onChange: (value: V) => void;
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-md border border-input p-0.5">
      {options.map(({ value: option, label: text, icon: Icon }) => (
        <button
          key={option}
          type="button"
          aria-pressed={option === value}
          onClick={() => onChange(option)}
          className={cn(
            "inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded px-3 text-sm font-medium",
            option === value ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-muted",
          )}
        >
          {Icon ? <Icon className="size-4" aria-hidden /> : null}
          <span>{text}</span>
        </button>
      ))}
    </div>
  );
}

/** Test ids on the two panes' scrolling elements, which the scroll area renders itself. */
function markPane(id: string) {
  return (element: HTMLDivElement | null) => element?.setAttribute("data-testid", id);
}
const markPrimaryPane = markPane("split-primary");
const markDetailPane = markPane("split-detail");

/**
 * A list beside its detail on wide screens; only the detail on narrow ones, when there is one. Side by side, the
 * two fill the page's height and each scrolls on its own: scrolling the detail never moves the list, or the page.
 */
export function SplitView({ primary, detail, detailLabel }: {
  primary: ReactNode;
  detail?: ReactNode;
  detailLabel?: string;
}) {
  if (!detail) return <div className="min-w-0">{primary}</div>;
  // The page's own area, less <main>'s padding (py-6): the split fills what's on screen, so the page has nothing
  // left to scroll. The panes keep a little room inside for focus rings and the bar.
  const pane = "overscroll-contain px-1 xl:pe-3";
  return (
    <div data-testid="split" className="grid min-h-0 gap-6 xl:h-[calc(100dvh-3rem)] xl:grid-cols-[minmax(0,1fr)_minmax(34rem,55%)]">
      <ScrollArea className="-mx-1 hidden min-h-0 min-w-0 xl:flex" viewportClassName={pane} viewportRef={markPrimaryPane}>
        {primary}
      </ScrollArea>
      <aside aria-label={detailLabel} className="-mx-1 flex min-h-0 min-w-0 flex-col">
        <ScrollArea className="min-h-0 flex-1" viewportClassName={pane} viewportRef={markDetailPane}>
          {detail}
        </ScrollArea>
      </aside>
    </div>
  );
}
