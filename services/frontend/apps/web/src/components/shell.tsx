"use client";

import { formatNumber } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { GuideDock } from "@apply/kit";
import { Button, cn, Logo, LogoMark, ScrollArea, Sheet, SheetContent, SheetTitle, SheetTrigger } from "@apply/ui";
import { Document, List, Logout, Menu, Portfolio, Search, Settings, SidePanelClose, SidePanelOpen, StarFilled, Sun, Time, User, WarningAlt } from "@apply/ui/icons";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useState } from "react";

import { useAutoCounts } from "@/lib/auto";

import { Help } from "./help";
import { DEFAULT_PACK, useCurrentPack } from "@/lib/pack-choice";
import { useMe, usePacks, useSignOut, useVersion } from "@/lib/queries";
import { useSidebarCollapsed } from "@/lib/sidebar";

// Grouped as the HIG suggests for sidebars: what's new, finding, applying, then settings.
const NAV = [
  { group: null, items: [{ href: "/today", label: "shell.today", icon: Sun }] },
  {
    group: "shell.group.discover",
    items: [
      { href: "/matches", label: "shell.matches", icon: StarFilled },
      { href: "/searches", label: "shell.searches", icon: Search },
      { href: "/sources", label: "shell.sources", icon: List },
    ],
  },
  {
    group: "shell.group.apply",
    items: [
      { href: "/applications", label: "shell.applications", icon: Portfolio },
      { href: "/profiles", label: "shell.profiles", icon: User },
      { href: "/answers", label: "shell.answers", icon: Document },
    ],
  },
  {
    group: "shell.group.auto",
    items: [
      { href: "/ready", label: "shell.ready", icon: Time },
      { href: "/needs-you", label: "shell.needs_you", icon: WarningAlt },
    ],
  },
  { group: null, items: [{ href: "/settings", label: "shell.settings", icon: Settings }] },
] as const;

function Nav({ onNavigate, collapsed = false }: { onNavigate?: () => void; collapsed?: boolean }) {
  const { t, locale } = useI18n();
  const pathname = usePathname();
  const counts = useAutoCounts().data;
  const count: Record<string, number | undefined> = { "/ready": counts?.ready, "/needs-you": counts?.needs_you };
  return (
    <nav aria-label={t("shell.nav")} className="space-y-4">
      {NAV.map(({ group, items }, i) => (
        <div key={group ?? i}>
          {group ? <h2 className={cn("px-3 pb-1 text-xs font-semibold text-muted-foreground", collapsed && "sr-only")}>{t(group)}</h2> : null}
          <ul className="space-y-1">
            {items.map(({ href, label, icon: Icon }) => {
              const current = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <li key={href}>
                  <Link href={href} onClick={onNavigate} aria-current={current ? "page" : undefined}
                    title={collapsed ? t(label) : undefined}
                    className={cn(
                      "relative flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                      collapsed && "justify-center px-0",
                      current ? "bg-primary/10 text-primary" : "text-foreground",
                    )}>
                    <Icon className="size-5 shrink-0" aria-hidden />
                    <span className={cn(collapsed && "sr-only")}>{t(label)}</span>
                    {count[href] ? (
                      <span className={cn(
                        "rounded-full bg-muted px-2 py-0.5 text-xs font-semibold tabular-nums text-foreground",
                        collapsed ? "absolute -end-1 -top-1 px-1.5" : "ms-auto",
                      )}>
                        {formatNumber(count[href]!, locale)}
                      </span>
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

/** Which pack the screens work in: one place to switch context (HIG), remembered on this device. */
export function PackSwitcher() {
  const { t, pick } = useI18n();
  const packs = usePacks().data;
  const [pack, choose] = useCurrentPack();
  const known = packs?.some((p) => p.key === pack) ?? true;
  const current = known ? pack : DEFAULT_PACK; // a pack that's gone since: work in the default one
  return (
    <div className="space-y-1 px-1">
      <div className="flex items-center justify-between">
        <label htmlFor="pack-switcher" className="px-2 text-xs font-semibold text-muted-foreground">{t("shell.pack")}</label>
        <Help slug="packs" />
      </div>
      <select id="pack-switcher" value={current} onChange={(e) => choose(e.target.value)}
        className="flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base font-medium md:text-sm">
        {(packs ?? []).map((p) => <option key={p.key} value={p.key}>{pick(p.label)}</option>)}
        {packs ? null : <option value={current}>{t("state.loading")}</option>}
      </select>
    </div>
  );
}

/** Where each release is listed, with what changed: compared with the version shown, it says whether to update. */
const RELEASES = "https://github.com/sanjiblamichhane/apply/releases";

function Account({ collapsed = false }: { collapsed?: boolean }) {
  const { t } = useI18n();
  const me = useMe();
  const version = useVersion();
  const signOut = useSignOut();
  const router = useRouter();
  return (
    <div className="space-y-2 border-t pt-4">
      {me.data && !collapsed ? <p className="truncate px-3 text-sm text-muted-foreground" title={me.data.email}>{me.data.email}</p> : null}
      {version.data && !collapsed ? (
        <a href={RELEASES} target="_blank" rel="noreferrer"
          className="flex min-h-11 items-center rounded-md px-3 text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          {t("shell.version", { version: version.data })}<span className="sr-only">, {t("shell.version_hint")}</span>
        </a>
      ) : null}
      <Button variant="ghost" className={cn("w-full gap-3", collapsed ? "justify-center px-0" : "justify-start")}
        title={collapsed ? t("shell.sign_out") : undefined}
        onClick={() => signOut.mutate(undefined, { onSettled: () => router.replace("/sign-in") })}>
        <Logout className="size-5 shrink-0" aria-hidden />
        <span className={cn(collapsed && "sr-only")}>{t("shell.sign_out")}</span>
      </Button>
    </div>
  );
}

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  const { t } = useI18n();
  return (
    <Link href="/today" aria-label={t("app.name")}
      className={cn("flex min-h-11 items-center rounded-md px-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring", collapsed && "justify-center px-0")}>
      {collapsed ? <LogoMark /> : <Logo />}
    </Link>
  );
}

/** The element the page scrolls in has a fixed id, for tests and anything else that needs to find it. */
function markPageScroller(element: HTMLDivElement | null) {
  if (element) element.id = "page-scroller";
}

/** The app around every signed-in page: a sidebar on wide screens, a menu sheet on narrow ones. */
export function Shell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useSidebarCollapsed();
  return (
    // The window never scrolls: the sidebar and the page each scroll in their own area, so the
    // sidebar stays put while the page moves.
    <div className="flex h-dvh overflow-hidden">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-3 focus:shadow">
        {t("shell.skip")}
      </a>
      <aside id="sidebar" aria-label={t("shell.sidebar")}
        className={cn(
          "hidden h-full shrink-0 flex-col gap-6 border-r bg-card py-4 motion-safe:transition-[width] lg:flex",
          collapsed ? "w-16 px-2" : "w-60 px-3",
        )}>
        <div className={cn("flex items-center gap-1", collapsed ? "flex-col" : "justify-between")}>
          <Brand collapsed={collapsed} />
          <Button variant="ghost" size="icon" aria-controls="sidebar" aria-expanded={!collapsed}
            aria-label={collapsed ? t("shell.expand_sidebar") : t("shell.collapse_sidebar")}
            title={collapsed ? t("shell.expand_sidebar") : t("shell.collapse_sidebar")}
            onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? <SidePanelOpen aria-hidden /> : <SidePanelClose aria-hidden />}
          </Button>
        </div>
        {collapsed ? null : <PackSwitcher />}
        {/* The nav scrolls on its own when the window is short; the brand and the account stay in view. */}
        <ScrollArea className="-mx-1 min-h-0 flex-1" viewportClassName="px-1 overscroll-contain">
          <Nav collapsed={collapsed} />
        </ScrollArea>
        <Account collapsed={collapsed} />
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="z-40 flex shrink-0 items-center gap-2 border-b bg-card px-2 py-1 lg:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label={t("shell.open_menu")}>
                <Menu aria-hidden />
              </Button>
            </SheetTrigger>
            <SheetContent side="start" className="w-72 gap-6 p-6">
              <SheetTitle className="sr-only">{t("shell.nav")}</SheetTitle>
              <Brand />
              <PackSwitcher />
              <ScrollArea className="min-h-0 flex-1" viewportClassName="overscroll-contain">
                <Nav onNavigate={() => setOpen(false)} />
              </ScrollArea>
              <Account />
            </SheetContent>
          </Sheet>
          <Brand />
        </header>
        <ScrollArea className="min-h-0 flex-1" viewportRef={markPageScroller} viewportClassName="overscroll-contain">
          <main id="main" tabIndex={-1} className="min-w-0 px-4 py-6 focus:outline-none sm:px-6 lg:px-8">
            {children}
          </main>
        </ScrollArea>
      </div>
      {/* An open guide, on a wide screen: beside the page, which narrows to make room (a sheet when narrower). */}
      <GuideDock />
    </div>
  );
}
