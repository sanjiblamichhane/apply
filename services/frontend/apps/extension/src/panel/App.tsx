/**
 * The side panel: connect once with a token. **Copy** (the default) shows the profile beside any form: a click
 * puts a value on the clipboard (copy.tsx). Settings (language, clipboard, account) is a screen of its own. **Fill**, on a board's application form, finds the application in
 * apply (or tracks it), fills the form, and shows what was left for you. The person submits; the board's
 * thank-you page is recorded by the service worker, with Undo here.
 */
import type { FillSheet, Pack } from "@apply/api";
import { adapterFor, boardHosts, type FillResult, type PreviewRow } from "@apply/ats-adapters";
import { bestLocale, hasCatalogue, LANGUAGES, loadLocale, type Locale, LOCALES } from "@apply/i18n";
import { I18nProvider, useI18n } from "@apply/i18n/react";
import { Alert, AlertDescription, AlertTitle, Badge, Button, Input, Label, Logo } from "@apply/ui";
import { ChevronLeft, Clipboard, ExternalLink, MagicWand, Renew, Settings } from "@apply/ui/icons";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ExtensionApi } from "../api";
import { extensionStore } from "../extension-store";
import {
  cleanApiUrl, DEFAULT_API, forget, isBuiltInApi, loadConnection, localeOverride, saveConnection, type Connection,
} from "../config";
import {
  pendingKey, recordedKey, type Broadcast, type FileData, type FillReply, type PageInfo, type PendingFill, type Recorded,
  type PageChanged, type ToContent,
} from "../messages";
import { allowSite, forgetSite, originOf } from "../sites";
import { ClearSetting, CopyHelp, CopyView, Tip, Tool, ToolLink } from "./copy";
import { chooseTheme, savedTheme, type Theme, THEMES } from "../theme";
import { FILLS, Preview } from "./preview";
import { decide, filledSummary, toBase64, type Known } from "./state";

const local = extensionStore(chrome.storage.local);
const session = extensionStore(chrome.storage.session);
const pinnedTab = Number(new URLSearchParams(location.search).get("tab")) || null; // the journeys open the panel in a tab

async function targetTab(): Promise<chrome.tabs.Tab | null> {
  if (pinnedTab) return chrome.tabs.get(pinnedTab).catch(() => null);
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab ?? null;
}

function ask<T>(tabId: number, message: ToContent): Promise<T | null> {
  return chrome.tabs.sendMessage(tabId, message).then((r) => (r ?? null) as T | null).catch(() => null);
}

function errorCode(error: unknown): string {
  return (error as { code?: string })?.code ?? "INTERNAL";
}

export function App() {
  const [connection, setConnection] = useState<Connection | null | undefined>(undefined);
  const [override, setOverride] = useState<Locale | null>(null);
  useEffect(() => {
    void Promise.all([loadConnection(local), localeOverride(local)]).then(([c, l]) => {
      setConnection(c);
      setOverride(l);
      // The web app's address can change after connecting (or was missing before apply sent it): ask again, quietly.
      if (!c) return;
      void new ExtensionApi(c.apiUrl, c.token).whoami().then((caller) => {
        const webUrl = caller.web_url ?? null;
        if (webUrl === c.webUrl) return;
        const updated = { ...c, webUrl };
        setConnection(updated);
        void saveConnection(local, updated);
      }).catch(() => undefined);
    });
  }, []);
  const wanted: Locale = override ?? connection?.locale ?? bestLocale(navigator.languages);
  // A language's strings load before it's shown (until then, the one before stays), so nothing flashes in English.
  const [locale, setLocale] = useState<Locale>(() => (hasCatalogue(wanted) ? wanted : "en"));
  useEffect(() => {
    let live = true;
    void loadLocale(wanted).catch(() => null).then(() => { if (live) setLocale(wanted); });
    return () => { live = false; };
  }, [wanted]);
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);

  const chooseLocale = (next: Locale) => { setOverride(next); void local.set({ locale: next }); };
  return (
    <I18nProvider locale={locale}>
      {connection ? (
        <Panel connection={connection} locale={locale} onLocale={chooseLocale}
          onDisconnect={async () => { await forget(local); setConnection(null); }} />
      ) : (
        <div className="flex min-h-screen flex-col gap-4 p-4 text-base">
          <main className="flex flex-1 flex-col gap-4">
            {connection === null && <Connect onConnected={setConnection} />}
          </main>
          <footer className="border-t pt-3 text-sm text-muted-foreground">
            <LanguagePicker locale={locale} onLocale={chooseLocale} />
          </footer>
        </div>
      )}
    </I18nProvider>
  );
}

function LanguagePicker({ locale, onLocale }: { locale: Locale; onLocale: (l: Locale) => void }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor="language" className="text-sm">{t("ext.language")}</Label>
      <select id="language" value={locale} onChange={(e) => onLocale(e.target.value as Locale)}
        className="h-11 rounded-md border bg-background px-3 text-sm text-foreground">
        {LOCALES.map((l) => <option key={l} value={l} lang={l}>{LANGUAGES[l].name}</option>)}
      </select>
    </div>
  );
}

/**
 * Match the system, Light or Dark: three radios drawn as one segmented control (each segment 44 px tall), painted at
 * once when chosen. Arrow keys move between them, as with any radio group.
 */
function ThemePicker() {
  const { t } = useI18n();
  const [theme, setTheme] = useState<Theme | null>(null);
  useEffect(() => { void savedTheme().then(setTheme); }, []);
  const choose = (next: Theme) => { setTheme(next); chooseTheme(next); };
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-sm font-medium">{t("settings.appearance")}</legend>
      <div className="flex rounded-md border border-input p-0.5">
        {THEMES.map((value) => (
          <label key={value}
            className={`flex min-h-11 flex-1 cursor-pointer items-center justify-center rounded px-2 text-center text-sm has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-ring ${
              theme === value ? "bg-primary font-semibold text-primary-foreground" : "text-foreground hover:bg-muted"}`}>
            <input type="radio" name="theme" value={value} className="sr-only" checked={theme === value}
              onChange={() => choose(value)} />
            {t(`settings.appearance.${value}`)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function Connect({ onConnected }: { onConnected: (c: Connection) => void }) {
  const { t, error } = useI18n();
  const [address, setAddress] = useState(DEFAULT_API);
  const [token, setToken] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setProblem(null);
    const apiUrl = cleanApiUrl(address);
    if (!apiUrl) { setProblem(error("VALIDATION_FAILED")); return; }
    setBusy(true);
    try {
      if (!isBuiltInApi(apiUrl)) {
        const granted = await chrome.permissions.request({ origins: [`${apiUrl}/*`] });
        if (!granted) { setProblem(t("ext.connect.denied")); return; }
      }
      const caller = await new ExtensionApi(apiUrl, token.trim()).whoami();
      const connection: Connection = {
        apiUrl, token: token.trim(), email: caller.email, locale: caller.locale, webUrl: caller.web_url ?? null,
      };
      await saveConnection(local, connection);
      onConnected(connection);
    } catch (e) {
      setProblem(error(errorCode(e)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <Logo title={t("app.name")} />
      <h1 className="text-xl font-semibold">{t("ext.connect.title")}</h1>
      <p className="text-muted-foreground">{t("ext.connect.body")}</p>
      <div className="flex flex-col gap-2">
        <Label htmlFor="address">{t("ext.connect.address")}</Label>
        <Input id="address" type="url" value={address} onChange={(e) => setAddress(e.target.value)}
          aria-describedby="address-hint" autoComplete="url" />
        <p id="address-hint" className="text-sm text-muted-foreground">{t("ext.connect.address_hint")} {t("ext.connect.permission")}</p>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="token">{t("ext.connect.token")}</Label>
        <Input id="token" type="password" value={token} onChange={(e) => setToken(e.target.value)} required
          autoComplete="off" spellCheck={false} aria-invalid={problem ? true : undefined}
          aria-describedby={problem ? "connect-problem" : undefined} />
      </div>
      {problem && <p id="connect-problem" role="alert" className="text-sm text-destructive">{problem}</p>}
      <Button type="submit" disabled={busy || !token.trim()}>{t("ext.connect.submit")}</Button>
    </form>
  );
}

const VIEW = "panelView";
type View = "copy" | "fill";

/**
 * The connected panel, one page that switches views: a pinned bar with Copy | Fill and Settings. Settings is its
 * own screen (Back returns), so the language, the clipboard setting and the account take no room beside the values.
 * The Copy | Fill choice is remembered while the browser is open.
 */
function Panel({ connection, locale, onLocale, onDisconnect }: {
  connection: Connection; locale: Locale; onLocale: (l: Locale) => void; onDisconnect: () => void;
}) {
  const { t } = useI18n();
  const api = useMemo(() => new ExtensionApi(connection.apiUrl, connection.token), [connection]);
  const [view, setView] = useState<View | null>(null);
  const [settings, setSettings] = useState(false);
  const back = useRef<HTMLButtonElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    void session.get(VIEW).then((v) => setView((v[VIEW] as View | undefined) ?? "copy"));
  }, []);
  // Focus follows the screen: Back when Settings opens, the Settings button when it closes.
  const shown = useRef(false);
  useEffect(() => {
    if (settings) back.current?.focus();
    else if (shown.current) opener.current?.focus();
    shown.current = true;
  }, [settings]);
  const choose = (next: View) => { setView(next); void session.set({ [VIEW]: next }); };
  const views: View[] = ["copy", "fill"];
  const move = (event: React.KeyboardEvent) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = view === "copy" ? "fill" : "copy";
    choose(next);
    document.getElementById(`view-${next}`)?.focus();
  };
  if (view === null) return null;
  const bar = "sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background px-3";
  if (settings) {
    return (
      <div className="flex min-h-screen flex-col text-base">
        <header className={bar}>
          <Button ref={back} variant="ghost" size="sm" className="-ms-2 min-h-11" onClick={() => setSettings(false)}>
            <ChevronLeft aria-hidden className="size-4" />{t("ext.back")}
          </Button>
        </header>
        <main className="flex flex-col gap-5 p-4">
          <h1 className="text-lg font-semibold">{t("ext.settings")}</h1>
          <LanguagePicker locale={locale} onLocale={onLocale} />
          <ThemePicker />
          <section className="flex flex-col gap-3" aria-labelledby="settings-copy">
            <h2 id="settings-copy" className="text-base font-semibold">{t("ext.view.copy")}</h2>
            <CopyHelp />
            <ClearSetting />
          </section>
          <section className="flex flex-col gap-2 border-t pt-4" aria-labelledby="settings-account">
            <h2 id="settings-account" className="text-base font-semibold">{t("ext.account")}</h2>
            <p className="text-sm text-muted-foreground">{t("ext.connected_as", { email: connection.email })}</p>
            <Button variant="outline" className="self-start" onClick={onDisconnect}>{t("ext.disconnect")}</Button>
          </section>
        </main>
      </div>
    );
  }
  // Copy | Fill as icon tabs, then apply (a new tab) and Settings: the end of the one row at the top (Copy puts its own tools first).
  const actions = (
    <>
      <div role="tablist" aria-label={t("ext.views")} className="flex shrink-0 gap-0.5 border-s ps-1">
        {views.map((v) => {
          const label = t(v === "copy" ? "ext.view.copy" : "ext.view.fill");
          const Icon = v === "copy" ? Clipboard : MagicWand;
          return (
            <Tip key={v} label={label}>
            <button id={`view-${v}`} type="button" role="tab" aria-selected={view === v} aria-controls={`view-panel-${v}`}
              aria-label={label} tabIndex={view === v ? 0 : -1} onClick={() => choose(v)} onKeyDown={move}
              className={`flex size-9 items-center justify-center rounded-md focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring ${
                view === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>
              <Icon aria-hidden className="size-4" />
            </button>
            </Tip>
          );
        })}
      </div>
      {connection.webUrl && (
        <ToolLink label={t("ext.open_apply")} href={connection.webUrl}>
          <ExternalLink aria-hidden />
        </ToolLink>
      )}
      <Tool label={t("ext.settings")} onClick={() => setSettings(true)} ref={opener}>
        <Settings aria-hidden />
      </Tool>
    </>
  );
  return (
    <div className="flex min-h-screen flex-col text-base">
      <main role="tabpanel" id={`view-panel-${view}`} aria-labelledby={`view-${view}`} className="flex flex-1 flex-col">
        {view === "copy" ? <CopyView api={api} actions={actions} /> : (
          <FillPanel connection={connection} api={api} actions={actions} />
        )}
      </main>
    </div>
  );
}

function FillPanel({ connection, api, actions }: { connection: Connection; api: ExtensionApi; actions: React.ReactNode }) {
  const { t, error } = useI18n();
  const [tab, setTab] = useState<chrome.tabs.Tab | null>(null);
  const [known, setKnown] = useState<Known>({ connected: true });
  const [stages, setStages] = useState<Pack["pipeline"]["stages"]>([]);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const generation = useRef(0);
  const shown = useRef<number | undefined>(undefined);

  const refresh = useCallback(async () => {
    const run = ++generation.current;
    const current = await targetTab();
    if (run !== generation.current) return;
    setTab(current);
    shown.current = current?.id;
    if (!current?.id) { setKnown({ connected: true, page: null }); return; }
    const page = await ask<PageInfo>(current.id, { type: "page" });
    const onBoardHost = !!current.url && (adapterFor(current.url) !== null || boardHosts().some((h) => current.url!.includes(h)));
    const recorded = ((await session.get(recordedKey(current.id)))[recordedKey(current.id)] ?? null) as Recorded | null;
    let next: Known = { connected: true, page, onBoardHost, recorded };
    if (page?.isForm && page.ready) {
      try {
        const lookup = await api.lookup(page.postingUrls);
        next = { ...next, lookup };
        if (lookup?.application) next.sheet = await api.fillSheet(lookup.application.id);
      } catch (e) {
        setProblem(error(errorCode(e)));
      }
    }
    if (run !== generation.current) return;
    // A result stays with its form: the same application and the same step.
    setKnown((before) => {
      const same = before.sheet?.application.id === next.sheet?.application.id && before.resultFor === page?.formKey;
      return { ...next, result: same ? before.result : null, resultFor: same ? before.resultFor : undefined };
    });
  }, [api, error]);

  useEffect(() => {
    // refresh() sets state only after awaiting the tab and the page: never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
    // A page load finishing, or a board drawn by script moving to another address without one.
    const onUpdated = (tabId: number, info: { status?: string; url?: string }) => {
      if ((pinnedTab ? tabId === pinnedTab : true) && (info.status === "complete" || info.url)) void refresh();
    };
    const onActivated = () => { if (!pinnedTab) void refresh(); };
    const onMessage = (message: Broadcast | PageChanged, sender: chrome.runtime.MessageSender) => {
      if (message.type === "recorded") void refresh();
      // The page said it changed (a sign-in done, a form's next step drawn): only the tab the panel is showing.
      else if (message.type === "page-changed" && sender.tab?.id !== undefined && sender.tab.id === shown.current) void refresh();
    };
    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.onActivated.addListener(onActivated);
    chrome.runtime.onMessage.addListener(onMessage);
    return () => {
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onActivated.removeListener(onActivated);
      chrome.runtime.onMessage.removeListener(onMessage);
    };
  }, [refresh]);

  const view = decide(known);
  // A form drawn by script, or a posting being read: look again shortly.
  useEffect(() => {
    if (view.kind !== "waiting") return;
    const timer = setTimeout(() => void refresh(), 700);
    return () => clearTimeout(timer);
  }, [view.kind, known, refresh]);

  const pack = known.sheet?.opportunity.pack;
  useEffect(() => {
    if (pack && stages.length === 0) void api.pack(pack).then((p) => setStages(p.pipeline.stages)).catch(() => undefined);
  }, [api, pack, stages.length]);

  // What a fill would do, asked of the page whenever a form is ready: again after a fill, and when the person comes
  // back to the panel (what they typed meanwhile shows as already filled). null: not asked yet, or a page whose
  // script predates the preview (reloading it brings it); the Fill button then works as before, without a list.
  const [rows, setRows] = useState<PreviewRow[] | null>(null);
  const [looked, setLooked] = useState(0);
  const readySheet = view.kind === "ready" ? view.sheet : null;
  const formKey = view.kind === "ready" ? view.page.formKey : "";
  useEffect(() => {
    const again = () => setLooked((n) => n + 1);
    window.addEventListener("focus", again);
    return () => window.removeEventListener("focus", again);
  }, []);
  useEffect(() => {
    if (!tab?.id || !readySheet) return;
    let live = true;
    const sheet = { values: readySheet.values, answers: readySheet.answers, documents: readySheet.documents };
    void ask<PreviewRow[]>(tab.id, { type: "preview", sheet }).then((r) => { if (live) setRows(Array.isArray(r) ? r : null); });
    return () => { live = false; };
  }, [tab?.id, readySheet, formKey, known.result, looked]);

  // Check the form again, when the person asks: the page read afresh, the profile and answers fetched again from
  // apply (an edit made since counts), and the matching run again. Rules in the extension, not a model.
  const [checking, setChecking] = useState(false);
  const [checked, setChecked] = useState("");
  const check = async () => {
    setChecking(true); setProblem(null); setChecked("");
    try {
      await refresh();
      setLooked((n) => n + 1);
      setChecked(t("ext.fill.checked"));
    } finally {
      setChecking(false);
    }
  };

  const track = async () => {
    if (!tab?.id || view.kind !== "untracked") return;
    setBusy(true); setProblem(null);
    try {
      const html = (await ask<string>(tab.id, { type: "html" })) ?? "";
      await api.track(view.page.postingUrls[0] ?? view.page.url, html, view.opportunity ?? undefined);
      await refresh();
    } catch (e) {
      setProblem(error(errorCode(e)));
    } finally {
      setBusy(false);
    }
  };

  const fill = async (skip: string[]) => {
    if (!tab?.id || view.kind !== "ready") return;
    setBusy(true); setProblem(null);
    try {
      const files: FileData[] = [];
      for (const doc of view.sheet.documents) {
        files.push({ document_type: doc.document_type, filename: doc.filename, base64: toBase64(await api.pdf(doc.pdf_path)) });
      }
      const sheet = { values: view.sheet.values, answers: view.sheet.answers, documents: view.sheet.documents };
      const reply = await ask<FillReply>(tab.id, { type: "fill", sheet, files, skip });
      if (!reply) { setKnown((k) => ({ ...k, page: null })); return; }
      if (!reply.ok) throw new Error(reply.error);
      const pending: PendingFill = { applicationId: view.sheet.application.id, filled: filledSummary(reply.result), at: Date.now() };
      await session.set({ [pendingKey(tab.id)]: pending });
      await session.remove(recordedKey(tab.id));
      setRows(null); // asked again for the form as it is now, rather than show the list from before
      setKnown((k) => ({ ...k, result: reply.result, resultFor: view.page.formKey, recorded: null }));
    } catch (e) {
      setProblem(error(errorCode(e)));
    } finally {
      setBusy(false);
    }
  };

  const undo = async (recorded: Recorded) => {
    if (!tab?.id || !recorded.submissionId) return;
    setBusy(true); setProblem(null);
    try {
      await api.undo(recorded.submissionId);
      await session.set({ [recordedKey(tab.id)]: { ...recorded, undone: true } satisfies Recorded });
      await refresh();
    } catch (e) {
      setProblem(error(errorCode(e)));
    } finally {
      setBusy(false);
    }
  };

  const site = originOf(tab?.url);
  const allow = async () => {
    if (!tab?.id || !site) return;
    setProblem(null);
    try {
      // First, in the click: the browser asks the person.
      if (!(await allowSite(tab.id, site))) { setProblem(t("ext.site.denied")); return; }
      await refresh();
    } catch (e) {
      setProblem(String(e));
    }
  };
  const forget = async () => {
    if (!site) return;
    await forgetSite(site).catch(() => undefined);
    setKnown({ connected: true, page: null });
  };

  const stageLabel = (code?: string) => {
    const stage = stages.find((s) => s.code === code);
    return stage ? stage : null;
  };

  return (
    <>
      <header className="sticky top-0 z-20 flex h-12 items-center gap-0.5 border-b bg-background px-2">
        <p className="min-w-0 flex-1 truncate px-1 text-sm font-semibold">{t("ext.view.fill")}</p>
        <Tool label={t("ext.fill.check")} onClick={() => void check()} disabled={checking || busy}>
          <Renew aria-hidden className={checking ? "animate-spin motion-reduce:animate-none" : undefined} />
        </Tool>
        {actions}
      </header>
      <div className="flex flex-col gap-4 p-4">
      {problem && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{problem}</AlertDescription>
        </Alert>
      )}
      <Body view={view} busy={busy} connection={connection} onTrack={track} onFill={fill} onUndo={undo} rows={rows}
        stageName={(code) => stageLabel(code)?.label} site={known.page === null && !known.onBoardHost ? site : null}
        onAllow={allow} />
      {known.page?.board === "other" && site && (
        <Button variant="ghost" className="self-start" onClick={forget}>
          {t("ext.site.forget", { site: new URL(site).host })}
        </Button>
      )}
      {view.kind === "loading" && <p className="sr-only" role="status">{t("ext.loading")}</p>}
      <p className="sr-only" role="status" aria-live="polite">{checked}</p>
      </div>
    </>
  );
}

function Body({ view, busy, connection, onTrack, onFill, onUndo, stageName, site, onAllow, rows }: {
  view: ReturnType<typeof decide>; busy: boolean; connection: Connection; rows: PreviewRow[] | null;
  onTrack: () => void; onFill: (skip: string[]) => void; onUndo: (r: Recorded) => void;
  stageName: (code?: string) => { en: string; ne: string } | undefined;
  site: string | null; onAllow: () => void;
}) {
  const { t, pick, error } = useI18n();
  switch (view.kind) {
    case "loading":
      return <p className="text-muted-foreground" aria-hidden="true">{t("ext.loading")}</p>;
    case "connect":
      return null;
    case "unsupported":
      return (
        <section className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">{t("ext.unsupported.title")}</h1>
          <p className="text-muted-foreground">{t("ext.unsupported.body")}</p>
          {site && (
            <div className="flex flex-col gap-2 border-t pt-3">
              <Button onClick={onAllow} aria-describedby="allow-hint">{t("ext.site.allow", { site: new URL(site).host })}</Button>
              <p id="allow-hint" className="text-sm text-muted-foreground">{t("ext.site.allow_hint")}</p>
            </div>
          )}
        </section>
      );
    case "sign_in":
      return (
        <section className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">{t("ext.sign_in.title")}</h1>
          <p className="text-muted-foreground">{t("ext.sign_in.body")}</p>
        </section>
      );
    case "job_page":
      return (
        <section className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">{t("ext.unsupported.title")}</h1>
          <p className="text-muted-foreground">{t("ext.job_page.body")}</p>
        </section>
      );
    case "reload":
      return (
        <section className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">{t("ext.unsupported.title")}</h1>
          <p className="text-muted-foreground">{t("ext.reload_page")}</p>
        </section>
      );
    case "waiting":
      return (
        <section className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold">{t("ext.loading")}</h1>
          <p className="text-muted-foreground" role="status">{t("ext.waiting_form")}</p>
        </section>
      );
    case "untracked":
      return (
        <section className="flex flex-col gap-3">
          <h1 className="text-xl font-semibold">{view.opportunity?.title || view.page.title}</h1>
          <p className="font-medium">{t("ext.untracked.title")}</p>
          <p className="text-muted-foreground">{t("ext.untracked.body")}</p>
          <Button onClick={onTrack} disabled={busy}>{busy ? t("ext.tracking") : t("ext.track")}</Button>
        </section>
      );
    case "ready":
      // Keyed by the form: a new step starts with every field ticked again.
      return <Ready key={view.page.formKey} sheet={view.sheet} result={view.result} steps={view.page.steps} busy={busy}
        connection={connection} onFill={onFill} rows={rows} />;
    case "recorded": {
      const r = view.recorded;
      if (r.error) {
        return (
          <section className="flex flex-col gap-3">
            <h1 className="text-xl font-semibold">{t("ext.record_failed")}</h1>
            <p className="text-muted-foreground">{error(r.error)}</p>
            <OpenInApply connection={connection} applicationId={r.applicationId} />
          </section>
        );
      }
      const stage = stageName(r.stageCode);
      return (
        <section className="flex flex-col gap-3">
          <h1 className="text-xl font-semibold">{r.undone ? t("ext.undone") : t("ext.recorded")}</h1>
          {!r.undone && stage && <p role="status">{t("ext.moved_to", { stage: pick(stage) })}</p>}
          {!r.undone && r.submissionId && (
            <Button variant="outline" onClick={() => onUndo(r)} disabled={busy}>{t("ext.undo")}</Button>
          )}
          <OpenInApply connection={connection} applicationId={r.applicationId} />
        </section>
      );
    }
  }
}

function OpenInApply({ connection, applicationId }: { connection: Connection; applicationId: string }) {
  const { t } = useI18n();
  if (!connection.webUrl) return null;
  return (
    <a className="inline-flex min-h-11 items-center text-sm font-medium text-primary underline underline-offset-4"
      href={`${connection.webUrl}/applications/${applicationId}`} target="_blank" rel="noreferrer">
      {t("ext.open_in_apply")}
    </a>
  );
}

function Ready({ sheet, result, steps, busy, connection, onFill, rows }: {
  sheet: FillSheet; result: FillResult | null; steps: boolean; busy: boolean; connection: Connection;
  onFill: (skip: string[]) => void; rows: PreviewRow[] | null;
}) {
  const { t, pick } = useI18n();
  const [skipped, setSkipped] = useState<ReadonlySet<string>>(new Set());
  const toggle = (key: string) => setSkipped((before) => {
    const next = new Set(before);
    if (!next.delete(key)) next.add(key);
    return next;
  });
  const ticked = rows ? rows.filter((r) => FILLS.includes(r.status) && !skipped.has(r.key)).length : null;
  const skip = rows ? rows.filter((r) => skipped.has(r.key)).map((r) => r.key) : [];
  return (
    <section className="flex flex-col gap-4" aria-labelledby="job-title">
      <div>
        <h1 id="job-title" className="text-xl font-semibold">{sheet.opportunity.title}</h1>
        <p className="text-muted-foreground">{sheet.opportunity.issuer_name}</p>
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{t("ext.documents")}</h2>
        {sheet.documents.length === 0 ? (
          <>
            <p className="text-muted-foreground">{t("ext.no_documents")}</p>
            <OpenInApply connection={connection} applicationId={sheet.application.id} />
          </>
        ) : (
          <ul className="flex flex-col gap-2">
            {sheet.documents.map((d) => (
              <li key={d.document_id} className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{pick(d.label)}</span>
                <Badge variant={d.reviewed ? "success" : "muted"}>{d.reviewed ? t("ext.doc_reviewed") : t("ext.doc_not_reviewed")}</Badge>
                {d.open_warnings > 0 && <Badge variant="outline">{t("ext.doc_warnings", { count: d.open_warnings })}</Badge>}
              </li>
            ))}
          </ul>
        )}
      </div>
      {result && <Result result={result} sheet={sheet} />}
      {rows && !(result && ticked === 0) && <Preview rows={rows} skipped={skipped} onToggle={toggle} busy={busy} />}
      {/* Confirming is pressing this: nothing is written before. Pinned, so it's in reach under a long list. */}
      {!(result && ticked === 0) && (
        <div className="sticky bottom-0 -mx-4 flex flex-col gap-2 border-t bg-background px-4 py-3">
          <Button onClick={() => onFill(skip)} disabled={busy || ticked === 0}>
            {busy ? t("ext.filling") : result ? t("ext.fill_again") : t("ext.fill")}
          </Button>
          {steps && <p className="text-sm text-muted-foreground">{t("ext.steps")}</p>}
        </div>
      )}
    </section>
  );
}

function Result({ result, sheet }: { result: FillResult; sheet: FillSheet }) {
  const { t, pick } = useI18n();
  const names = result.attached.map((type) => {
    const doc = sheet.documents.find((d) => d.document_type === type);
    return doc ? pick(doc.label) : type;
  });
  return (
    <div className="flex flex-col gap-3" role="status">
      <Alert>
        <AlertTitle>{t("ext.filled", { count: result.filled })}</AlertTitle>
        <AlertDescription>
          {names.length > 0 && <p>{t("ext.attached", { files: names.join(", ") })}</p>}
          <p>{t("ext.check_then_submit")}</p>
        </AlertDescription>
      </Alert>
      {result.leftBlank.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-base font-semibold">{t("ext.left_for_you")}</h2>
          <ul className="flex flex-col gap-2">
            {result.leftBlank.map((b) => (
              <li key={b.label} className="rounded-md border p-3">
                <p className="font-medium">{b.label}{b.required && <span className="text-muted-foreground"> · {t("ext.required")}</span>}</p>
                <p className="text-sm text-muted-foreground">{t(`ext.reason.${b.reason}`)}</p>
                {b.suggestion && <p className="text-sm">{t("ext.suggestion", { answer: b.suggestion })}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
