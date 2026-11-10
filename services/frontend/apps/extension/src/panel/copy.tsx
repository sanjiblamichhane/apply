/**
 * The copy panel: the person's profile beside any form, on any site. A click puts a value on the clipboard;
 * the person pastes it where it goes. Nothing on the page is touched, and no site permission is needed.
 *
 * Built to need as little scrolling as possible. One row at the top holds the profile (a searchable list) and
 * every tool as an icon; the sections wrap under it, and both stay pinned. Short values sit as many to a row as
 * fit. Each job or qualification folds to one line. Search (the icon, or "/") copies its first match on Enter. Each profile's sheet is kept in session storage
 * (memory, gone when the browser closes), and the other profiles are fetched quietly, so switching is instant.
 * Sensitive answers stay hidden until "Show".
 */
import type { CopyItem, CopySheet, CopyTab } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { Alert, AlertDescription, Button, Label, Tooltip, TooltipContent, TooltipTrigger } from "@apply/ui";
import { Checkmark, ChevronDown, Copy, Renew, Search } from "@apply/ui/icons";
import { forwardRef, useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import type { ExtensionApi } from "../api";
import { extensionStore } from "../extension-store";
import { copyText, matches, pasteKeys } from "../clipboard";
import { CLEAR_CLIPBOARD, CLIPBOARD_PERMISSIONS, type ToBackground } from "../messages";

const local = extensionStore(chrome.storage.local);
const session = extensionStore(chrome.storage.session);
const CACHE = "copySheets"; // { [profileId]: CopySheet }, and "" for the default
const PROFILE = "copyProfile";
const SHORT = 24; // a value this short, on one line, gets half a row
const PREFETCH = 5; // other profiles fetched quietly after the first

type Sheets = Record<string, CopySheet>;
type Status = { kind: "loading" } | { kind: "ready"; sheet: CopySheet } | { kind: "error"; code: string };
type Copier = (key: string, item: CopyItem, label: string) => void;
type Found = { tab: CopyTab; group: CopyTab["groups"][number]; item: CopyItem; key: string };

const isShort = (item: CopyItem) => !item.sensitive && item.value.length <= SHORT && !item.value.includes("\n");

export function CopyView({ api, actions }: { api: ExtensionApi; actions: ReactNode }) {
  const { t, error, pick } = useI18n();
  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [profileId, setProfileId] = useState<string | null>(null);
  const [tab, setTab] = useState("basics");
  const [query, setQuery] = useState("");
  const [said, setSaid] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [searching, setSearching] = useState(false);
  const run = useRef(0);
  const sheets = useRef<Sheets>({});
  const search = useRef<HTMLInputElement>(null);

  const remember = useCallback(async (key: string, sheet: CopySheet) => {
    sheets.current = { ...sheets.current, [key]: sheet };
    if (sheet.profile) sheets.current[sheet.profile.id] = sheet;
    await session.set({ [CACHE]: sheets.current });
  }, []);

  const prefetch = useCallback(async (sheet: CopySheet) => {
    const others = sheet.profiles.filter((p) => p.id !== sheet.profile?.id && !sheets.current[p.id]).slice(0, PREFETCH);
    for (const p of others) {
      try { await remember(p.id, await api.copySheet(p.id)); } catch { /* fetched when chosen instead */ }
    }
  }, [api, remember]);

  const load = useCallback(async (chosen: string | null) => {
    const mine = ++run.current;
    setBusy(true);
    try {
      const sheet = await api.copySheet(chosen ?? undefined);
      if (mine !== run.current) return;
      setStatus({ kind: "ready", sheet });
      await remember(chosen ?? "", sheet);
      void prefetch(sheet);
    } catch (e) {
      if (mine === run.current) setStatus({ kind: "error", code: (e as { code?: string })?.code ?? "INTERNAL" });
    } finally {
      if (mine === run.current) setBusy(false);
    }
  }, [api, remember, prefetch]);

  useEffect(() => {
    void (async () => {
      const saved = (await local.get(PROFILE))[PROFILE] as string | undefined;
      sheets.current = ((await session.get(CACHE))[CACHE] as Sheets | undefined) ?? {};
      const cached = sheets.current[saved ?? ""];
      if (cached) setStatus({ kind: "ready", sheet: cached });
      setProfileId(saved ?? null);
      await load(saved ?? null);
    })();
  }, [load]);

  const choose = (id: string) => {
    setProfileId(id);
    const cached = sheets.current[id];
    if (cached) setStatus({ kind: "ready", sheet: cached });
    void local.set({ [PROFILE]: id });
    void load(id);
  };

  const copy: Copier = (key, item, label) => {
    // Started here, in the click (or the key press): nothing is awaited before the clipboard is written.
    const writing = copyText(item.value);
    void writing.then((ok) => {
      setSaid(ok ? t("ext.copy.copied", { label }) : "");
      setProblem(ok ? null : t("ext.copy.failed"));
      setCopied(ok ? key : null);
      if (ok) {
        const note: ToBackground = { type: "copied", text: item.value };
        chrome.runtime.sendMessage(note).catch(() => undefined);
      }
    });
  };

  // "Copied" stays on the value for a moment.
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(null), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  // "/" goes to the search from anywhere in the panel (as on many sites), unless typing somewhere already.
  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      event.preventDefault();
      setSearching(true);
      setTimeout(() => search.current?.focus());
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // One row at the top: the profile, then every tool as an icon (search, refresh, then the panel's own).
  const bar = (left: ReactNode, tools: ReactNode = null) => (
    <div className="flex h-12 items-center gap-0.5 px-2">
      <div className="min-w-0 flex-1">{left}</div>
      {tools}
      {actions}
    </div>
  );
  const alone = (body: ReactNode) => (
    <section className="flex flex-col" aria-labelledby="copy-title">
      <h1 id="copy-title" className="sr-only">{t("ext.view.copy")}</h1>
      <div className="sticky top-0 z-20 border-b bg-background">{bar(null)}</div>
      <div className="p-3">{body}</div>
    </section>
  );
  if (status.kind === "loading") return alone(<p role="status">{t("ext.loading")}</p>);
  if (status.kind === "error") {
    const missing = status.code === "TOKEN_SCOPE_MISSING";
    return alone(
      <Alert variant={missing ? "default" : "destructive"} role="alert">
        <AlertDescription>{missing ? t("ext.copy.scope_missing") : error(status.code)}</AlertDescription>
        {!missing && <Button variant="outline" className="mt-2" onClick={() => void load(profileId)}>{t("ext.copy.refresh")}</Button>}
      </Alert>,
    );
  }
  const { sheet } = status;
  if (!sheet.profile) return alone(<p>{t("ext.copy.no_profile")}</p>);
  const current = sheet.tabs.find((x) => x.key === tab) ?? sheet.tabs[0];
  const q = query.trim();
  const found: Found[] = q
    ? sheet.tabs.flatMap((tb) => tb.groups.flatMap((group, g) => group.items.map((item, i) => ({ tab: tb, group, item, key: `${tb.key}:${g}:${i}` }))))
      .filter(({ tab: tb, group, item }) => matches(q, pick(tb.label), group.title, pick(item.label), item.sensitive ? "" : item.value))
    : [];
  const first = found.find((f) => !f.item.sensitive);

  const onSearchKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && first) {
      event.preventDefault();
      copy(first.key, first.item, pick(first.item.label));
    } else if (event.key === "Escape") {
      event.preventDefault();
      if (query) setQuery("");
      else setSearching(false);
    }
  };
  const showSearch = searching || Boolean(query);
  const toggleSearch = () => {
    if (showSearch) { setQuery(""); setSearching(false); return; }
    setSearching(true);
    setTimeout(() => search.current?.focus());
  };

  return (
    <section className="flex flex-col" aria-labelledby="copy-title">
      <h1 id="copy-title" className="sr-only">{t("ext.view.copy")}</h1>
      <div className="sticky top-0 z-20 flex flex-col border-b bg-background">
        {bar(
          sheet.profiles.length > 1
            ? <ProfilePicker profiles={sheet.profiles} current={sheet.profile} onChoose={choose} />
            : <p className="truncate px-1 text-sm font-semibold">{sheet.profile.name}</p>,
          <>
            <Tool label={t("ext.copy.search")} onClick={toggleSearch} pressed={showSearch} controls="copy-search-row">
              <Search aria-hidden />
            </Tool>
            <Tool label={t("ext.copy.refresh")} onClick={() => void load(profileId)} disabled={busy}>
              <Renew aria-hidden className={busy ? "animate-spin motion-reduce:animate-none" : undefined} />
            </Tool>
          </>,
        )}
        {showSearch && (
          <div id="copy-search-row" className="relative px-2 pb-2">
            <Label htmlFor="copy-search" className="sr-only">{t("ext.copy.search")}</Label>
            <Search aria-hidden className="pointer-events-none absolute start-4.5 top-[1.125rem] size-4 -translate-y-1/2 text-muted-foreground" />
            <input id="copy-search" ref={search} type="search" value={query} autoComplete="off"
              onChange={(e) => setQuery(e.target.value)} onKeyDown={onSearchKey} aria-describedby="copy-search-hint"
              placeholder={t("ext.copy.search")}
              className="h-9 w-full rounded-md border border-input bg-background pe-2 ps-8 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring" />
            <span id="copy-search-hint" className="sr-only">{t("ext.copy.enter")}</span>
          </div>
        )}
        {!q && <div className="px-2 pb-2"><Tabs tabs={sheet.tabs} current={current?.key ?? ""} onChoose={setTab} /></div>}
      </div>

      <div className="flex flex-col gap-3 px-3 pb-4 pt-2">
        {problem && <Alert variant="destructive" role="alert"><AlertDescription>{problem}</AlertDescription></Alert>}
        {q ? (
          found.length === 0 ? <p className="text-sm">{t("ext.copy.none_found", { query: q })}</p> : (
            <>
              {first && <p className="text-xs text-muted-foreground">{t("ext.copy.enter")}</p>}
              <Grid>
                {found.map(({ item, key, group }) => (
                  <Tile key={key} id={key} item={item} context={group.title} copied={copied === key} onCopy={copy} />
                ))}
              </Grid>
            </>
          )
        ) : current && (
          <div role="tabpanel" id={`copy-panel-${current.key}`} aria-labelledby={`copy-tab-${current.key}`}
            className="flex flex-col gap-2">
            <TabBody key={`${sheet.profile.id}:${current.key}`} tab={current} copied={copied} onCopy={copy} />
          </div>
        )}
      </div>
      <p className="sr-only" role="status" aria-live="polite">{said}</p>
    </section>
  );
}

/**
 * A tooltip under a control in the top row, on hover or keyboard focus. The browser's side panel doesn't reliably show
 * native `title` tooltips, so this draws its own. The control keeps its own accessible name.
 */
export function Tip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="bottom" collisionPadding={8} className="px-2 py-1 text-xs">{label}</TooltipContent>
    </Tooltip>
  );
}

/** A tool in the top row: an icon, named for screen readers and in a tooltip. */
export const Tool = forwardRef<HTMLButtonElement, {
  label: string; onClick: () => void; disabled?: boolean; pressed?: boolean; controls?: string; children: ReactNode;
}>(({ label, onClick, disabled, pressed, controls, children }, ref) => (
  <Tip label={label}>
  <button ref={ref} type="button" onClick={onClick} disabled={disabled} aria-label={label}
    aria-expanded={controls ? pressed : undefined} aria-controls={controls && pressed ? controls : undefined}
    className={`flex size-9 shrink-0 items-center justify-center rounded-md hover:bg-muted disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring [&_svg]:size-4 ${
      pressed ? "bg-muted text-foreground" : "text-muted-foreground"}`}>
    {children}
  </button>
  </Tip>
));
Tool.displayName = "Tool";

/** A tool in the top row that opens a page in a new tab: a link, so it behaves like one. */
export function ToolLink({ label, href, children }: { label: string; href: string; children: ReactNode }) {
  return (
    <Tip label={label}>
    <a href={href} target="_blank" rel="noreferrer" aria-label={label}
      className="flex size-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring [&_svg]:size-4">
      {children}
    </a>
    </Tip>
  );
}

/**
 * The profile: one choice from a list that scrolls, with a search at its top, so it works the same for two
 * profiles or fifty. The search is a combobox (arrow keys move, Enter chooses, Escape closes).
 */
function ProfilePicker({ profiles, current, onChoose }: {
  profiles: CopySheet["profiles"]; current: NonNullable<CopySheet["profile"]>; onChoose: (id: string) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const shown = profiles.filter((p) => matches(filter.trim(), p.name));

  useEffect(() => {
    if (!open) return;
    const away = (event: MouseEvent) => { if (!box.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);
  useEffect(() => {
    list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const show = () => {
    setFilter("");
    setActive(Math.max(0, profiles.findIndex((p) => p.id === current.id)));
    setOpen(true);
  };
  const close = () => { setOpen(false); button.current?.focus(); };
  const pickOne = (id: string) => { onChoose(id); close(); };
  const onKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (shown.length) setActive((i) => (i + (event.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length);
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      setActive(event.key === "Home" ? 0 : Math.max(0, shown.length - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (shown[active]) pickOne(shown[active].id);
    } else if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  };

  return (
    <div ref={box} className="relative">
      <Tip label={current.name}>
      <button ref={button} type="button" aria-haspopup="listbox" aria-expanded={open}
        aria-label={`${t("ext.copy.profile")}: ${current.name}`}
        onClick={() => (open ? setOpen(false) : show())}
        className="flex h-9 w-full min-w-0 items-center gap-1 rounded-md px-2 text-start text-sm font-semibold hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring">
        <span className="min-w-0 flex-1 truncate">{current.name}</span>
        <ChevronDown aria-hidden className="size-4 shrink-0 text-muted-foreground" />
      </button>
      </Tip>
      {open && (
        <div className="absolute start-0 top-full z-30 mt-1 flex w-72 max-w-[calc(100vw-1rem)] flex-col gap-1 rounded-md border bg-popover p-1 text-popover-foreground shadow-lg">
          {/* eslint-disable-next-line jsx-a11y/no-autofocus -- the person opened the list to choose: typing filters it */}
          <input type="text" role="combobox" autoFocus value={filter} autoComplete="off"
            aria-label={t("ext.copy.find_profile")} placeholder={t("ext.copy.find_profile")}
            aria-expanded="true" aria-controls="copy-profiles" aria-autocomplete="list"
            aria-activedescendant={shown[active] ? `copy-profile-${shown[active].id}` : undefined}
            onChange={(e) => { setFilter(e.target.value); setActive(0); }} onKeyDown={onKey}
            className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring" />
          <ul ref={list} id="copy-profiles" role="listbox" aria-label={t("ext.copy.profile")}
            className="max-h-64 overflow-y-auto overscroll-contain">
            {shown.length === 0 && <li className="px-2 py-2 text-sm text-muted-foreground">{t("ext.copy.no_profile_match")}</li>}
            {shown.map((p, i) => (
              // Chosen with the mouse here, and with the keyboard from the search above (aria-activedescendant).
              // eslint-disable-next-line jsx-a11y/click-events-have-key-events
              <li key={p.id} id={`copy-profile-${p.id}`} role="option" aria-selected={p.id === current.id} data-index={i}
                onClick={() => pickOne(p.id)} onMouseMove={() => setActive(i)}
                className={`flex min-h-9 cursor-pointer items-center gap-2 rounded-sm px-2 text-sm ${i === active ? "bg-muted text-foreground" : ""}`}>
                <span className="min-w-0 flex-1 truncate">{p.name}</span>
                {p.id === current.id && <Checkmark aria-hidden className="size-4 shrink-0 text-primary" />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Tabs({ tabs, current, onChoose }: { tabs: CopyTab[]; current: string; onChoose: (key: string) => void }) {
  const { t, pick } = useI18n();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const move = (event: KeyboardEvent, index: number) => {
    const step = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: 1, ArrowUp: -1 }[event.key];
    const to = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : step === undefined ? -1
      : (index + step + tabs.length) % tabs.length;
    if (to < 0) return;
    event.preventDefault();
    onChoose(tabs[to]!.key);
    refs.current[to]?.focus();
  };
  return (
    <div role="tablist" aria-label={t("ext.copy.sections")} className="flex flex-wrap gap-1">
      {tabs.map((tab, i) => {
        const selected = tab.key === current;
        return (
          <button key={tab.key} ref={(el) => { refs.current[i] = el; }} type="button" role="tab"
            id={`copy-tab-${tab.key}`} aria-controls={`copy-panel-${tab.key}`} aria-selected={selected}
            tabIndex={selected ? 0 : -1} onClick={() => onChoose(tab.key)} onKeyDown={(e) => move(e, i)}
            className={`h-8 shrink-0 rounded-md px-2.5 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${
              selected ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-muted"}`}>
            {pick(tab.label)}
          </button>
        );
      })}
    </div>
  );
}

/** A tab's values; a group with a title (a job, a qualification) folds, and only the first starts open. */
function TabBody({ tab, copied, onCopy }: { tab: CopyTab; copied: string | null; onCopy: Copier }) {
  const [open, setOpen] = useState<Set<number>>(() => new Set([0]));
  const toggle = (g: number) => setOpen((was) => {
    const next = new Set(was);
    if (next.has(g)) next.delete(g); else next.add(g);
    return next;
  });
  return (
    <>
      {tab.groups.map((group, g) => {
        const items = (
          <Grid>
            {group.items.map((item, i) => {
              const key = `${tab.key}:${g}:${i}`;
              return <Tile key={key} id={key} item={item} copied={copied === key} onCopy={onCopy} />;
            })}
          </Grid>
        );
        if (!group.title) return <div key={g}>{items}</div>;
        const expanded = open.has(g);
        const region = `copy-group-${tab.key}-${g}`;
        return (
          <div key={g} className="flex flex-col gap-1">
            <h2 className="text-sm font-semibold">
              <button type="button" aria-expanded={expanded} aria-controls={region} onClick={() => toggle(g)}
                className="flex min-h-11 w-full items-center gap-2 rounded-md px-1 text-start hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
                <ChevronDown aria-hidden className={`size-4 shrink-0 transition-transform motion-reduce:transition-none ${expanded ? "" : "-rotate-90"}`} />
                <span className="min-w-0 flex-1 truncate">{group.title}</span>
              </button>
            </h2>
            <div id={region} hidden={!expanded}>{items}</div>
          </div>
        );
      })}
    </>
  );
}

function Grid({ children }: { children: ReactNode }) {
  // As many columns as fit (about 150 px each): two in a narrow panel, more as it widens.
  return <ul className="grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-1.5">{children}</ul>;
}

/** One value: a click copies it. Short ones take half a row; long ones the whole row, cut to two lines. */
function Tile({ id, item, context, copied, onCopy }: {
  id: string; item: CopyItem; context?: string; copied: boolean; onCopy: Copier;
}) {
  const { t, pick } = useI18n();
  const [shown, setShown] = useState(!item.sensitive);
  const [whole, setWhole] = useState(false);
  const label = pick(item.label);
  const short = isShort(item);
  const span = short ? "" : "col-span-full";

  if (!shown) {
    return (
      <li className={`${span} flex items-center justify-between gap-2 rounded-md bg-muted px-2.5 py-1.5`}>
        <span className="min-w-0">
          <span className="block truncate text-xs font-medium text-muted-foreground">{label}</span>
          <span className="block text-sm">{t("ext.copy.hidden")}</span>
        </span>
        <Button variant="outline" size="sm" className="min-h-11 shrink-0" onClick={() => setShown(true)}
          aria-label={`${t("ext.copy.show")}: ${label}`}>{t("ext.copy.show")}</Button>
      </li>
    );
  }
  const long = !short && (item.value.length > 90 || item.value.split("\n").length > 2);
  return (
    <li className={`${span} flex min-w-0 items-stretch gap-0.5`}>
      <button type="button" onClick={() => onCopy(id, item, label)} title={short ? item.value : undefined}
        className={`group flex min-h-11 min-w-0 flex-1 items-start gap-1.5 rounded-md px-2.5 py-1.5 text-start focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring ${
          copied ? "bg-muted ring-2 ring-primary" : "bg-muted hover:ring-1 hover:ring-muted-foreground"}`}>
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 gap-1 text-xs font-medium text-muted-foreground">
            <span className="truncate">{copied ? t("ext.copy.copied_short") : label}</span>
            {context && !copied ? <span className="truncate">· {context}</span> : null}
          </span>
          <span className={`block break-words text-sm text-foreground ${short ? "truncate" : whole ? "whitespace-pre-line" : "line-clamp-2"}`}>
            {item.value}
          </span>
        </span>
        {copied
          ? <Checkmark aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
          : <Copy aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100" />}
      </button>
      {long && (
        <button type="button" onClick={() => setWhole((w) => !w)} aria-expanded={whole}
          aria-label={`${whole ? t("ext.copy.less") : t("ext.copy.more")}: ${label}`} title={whole ? t("ext.copy.less") : t("ext.copy.more")}
          className="flex w-8 shrink-0 items-start justify-center rounded-md pt-2 text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring">
          <ChevronDown aria-hidden className={`size-4 transition-transform motion-reduce:transition-none ${whole ? "rotate-180" : ""}`} />
        </button>
      )}
    </li>
  );
}

/** How copying works, for Settings. */
export function CopyHelp() {
  const { t } = useI18n();
  return <p className="text-sm text-muted-foreground">{t("ext.copy.hint", { keys: pasteKeys() })} {t("ext.copy.enter")}</p>;
}

/** "Clear the clipboard a minute after copying": asks the browser for the clipboard permissions only when turned on. */
export function ClearSetting() {
  const { t } = useI18n();
  const [on, setOn] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    void Promise.all([local.get(CLEAR_CLIPBOARD), chrome.permissions.contains({ permissions: CLIPBOARD_PERMISSIONS })])
      .then(([saved, granted]) => setOn(Boolean(saved[CLEAR_CLIPBOARD]) && granted));
  }, []);
  const change = (next: boolean) => {
    setProblem(null);
    if (!next) {
      setOn(false);
      void local.set({ [CLEAR_CLIPBOARD]: false });
      void chrome.permissions.remove({ permissions: CLIPBOARD_PERMISSIONS }).catch(() => undefined);
      return;
    }
    // Shown on at once; asked in the click (the browser shows its own prompt), and off again if it says no.
    setOn(true);
    // Requested straight away (nothing awaited first): the browser only prompts inside the click.
    void chrome.permissions.request({ permissions: CLIPBOARD_PERMISSIONS })
      .catch(() => false)
      .then((granted) => {
        setOn(granted);
        void local.set({ [CLEAR_CLIPBOARD]: granted });
        if (!granted) setProblem(t("ext.copy.clear_denied"));
      });
  };
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-start gap-3">
        <input id="copy-clear" type="checkbox" className="mt-1 size-5 accent-[var(--primary)]" checked={on}
          onChange={(e) => change(e.target.checked)} aria-describedby="copy-clear-hint" />
        <Label htmlFor="copy-clear" className="text-sm leading-6">{t("ext.copy.clear")}</Label>
      </div>
      <p id="copy-clear-hint" className="text-sm text-muted-foreground">{t("ext.copy.clear_hint")}</p>
      {problem && <p role="alert" className="text-sm text-destructive">{problem}</p>}
    </div>
  );
}
