"use client";

/**
 * Settings → Extension and AI agents: make a token for the extension or for an AI agent (`apply mcp`; it can't
 * record submissions), its secret shown once with Copy; see which tokens exist and when they were last used, and
 * revoke one. Revoking can't be undone, so it asks first.
 */
import { isApiError, type CreatedToken, type Scope } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogTitle, AlertDialogTrigger, Badge, Button, Input, Label,
} from "@apply/ui";
import { Copy } from "@apply/ui/icons";
import { useId, useState } from "react";
import { toast } from "sonner";

import { Help } from "./help";
import {
  EXPIRIES, KIND_SCOPES, KINDS, sortTokens, tokenState, useCreateToken, useRevokeToken, useTokens, type TokenKind,
} from "@/lib/tokens";

export function TokensSection() {
  const { t, error, relative, date } = useI18n();
  const tokens = useTokens();
  const revoke = useRevokeToken();
  const [created, setCreated] = useState<CreatedToken | null>(null);

  return (
    <section aria-labelledby="tokens-heading" className="space-y-4 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-1"><h2 id="tokens-heading" className="text-lg font-semibold">{t("tokens.title")}</h2><Help slug="extension" /></div>
      <p className="text-sm text-muted-foreground">{t("tokens.description")}</p>
      <p className="text-sm text-muted-foreground">{t("tokens.install")}</p>
      <p className="text-sm text-muted-foreground">{t("tokens.agent_description")}</p>

      {created ? <Secret created={created} onDone={() => setCreated(null)} /> : <NewTokenForm onCreated={setCreated} />}

      <div className="space-y-2">
        <h3 className="font-medium">{t("tokens.list")}</h3>
        {tokens.error ? <ErrorNotice message={error(isApiError(tokens.error) ? tokens.error.code : "INTERNAL")} /> : null}
        {tokens.data && tokens.data.length === 0 ? <p className="text-sm text-muted-foreground">{t("tokens.none")}</p> : null}
        <ul className="divide-y rounded-lg border">
          {sortTokens(tokens.data ?? []).map((token) => {
            const state = tokenState(token);
            return (
              <li key={token.id} className="flex flex-wrap items-center gap-3 px-3 py-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    {token.name}
                    {token.kind === "agent" ? <Badge variant="muted">{t("tokens.kind.agent")}</Badge> : null}
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">{token.prefix}…</code>
                    {state !== "active" ? <Badge variant="muted">{t(state === "revoked" ? "tokens.revoked" : "tokens.expired")}</Badge> : null}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {token.scopes.map((s) => t(`tokens.scope.${s}`)).join(" · ")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t("tokens.created_at", { when: relative(token.created_at) })}
                    {" · "}
                    {token.last_used_at ? t("tokens.last_used", { when: relative(token.last_used_at) }) : t("tokens.never_used")}
                    {state === "active" ? ` · ${token.expires_at ? t("tokens.expires_on", { when: date(token.expires_at) }) : t("tokens.no_expiry")}` : ""}
                  </p>
                </div>
                {state === "active" ? (
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="outline" size="sm" aria-label={t("tokens.revoke_named", { name: token.name })}>{t("tokens.revoke")}</Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogTitle>{t("tokens.revoke_title", { name: token.name })}</AlertDialogTitle>
                      <AlertDialogDescription>{t("tokens.revoke_body")}</AlertDialogDescription>
                      <AlertDialogFooter>
                        <AlertDialogCancel>{t("action.cancel")}</AlertDialogCancel>
                        <AlertDialogAction onClick={() => revoke.mutate(token.id, {
                          onSuccess: () => toast(t("tokens.revoked_toast")),
                          onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")),
                        })}>{t("tokens.revoke")}</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

function NewTokenForm({ onCreated }: { onCreated: (c: CreatedToken) => void }) {
  const { t, error } = useI18n();
  const create = useCreateToken();
  const [kind, setKind] = useState<TokenKind>("extension");
  const [name, setName] = useState(() => t("tokens.default_name"));
  const [scopes, setScopes] = useState<Scope[]>([...KIND_SCOPES.extension]);
  const kindName = useId();
  const allowed = KIND_SCOPES[kind];
  const choose = (next: TokenKind) => {
    setKind(next);
    setScopes([...KIND_SCOPES[next]]);
    // The suggested name follows the kind, unless the person has typed their own.
    if (name === t(kind === "agent" ? "tokens.default_name_agent" : "tokens.default_name")) {
      setName(t(next === "agent" ? "tokens.default_name_agent" : "tokens.default_name"));
    }
  };
  const [expiry, setExpiry] = useState<string>("never"); // the extension stays connected until you revoke it
  const expiryName = useId();

  return (
    <form className="space-y-3 rounded-lg border p-3" onSubmit={(e) => {
      e.preventDefault();
      create.mutate(
        { name, kind, scopes, expires_in_days: expiry === "never" ? null : (Number(expiry) as 30 | 90 | 365) },
        { onSuccess: onCreated },
      );
    }}>
      <fieldset className="space-y-1">
        <legend className="text-sm font-medium">{t("tokens.kind")}</legend>
        <div className="flex flex-wrap gap-2">
          {KINDS.map((value) => (
            <label key={value} className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
              <input type="radio" name={kindName} value={value} checked={kind === value} onChange={() => choose(value)} className="size-4 accent-[var(--primary)]"
                aria-describedby={value === "agent" && kind === "agent" ? "token-kind-hint" : undefined} />
              {t(`tokens.kind.${value}`)}
            </label>
          ))}
        </div>
        {kind === "agent" ? <p id="token-kind-hint" className="text-sm text-muted-foreground">{t("tokens.kind.agent_hint")}</p> : null}
      </fieldset>
      <div className="space-y-1">
        <Label htmlFor="token-name">{t("tokens.name")}</Label>
        <Input id="token-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} aria-describedby="token-name-hint" />
        <p id="token-name-hint" className="text-sm text-muted-foreground">{t("tokens.name_hint")}</p>
      </div>
      <fieldset className="space-y-1">
        <legend className="text-sm font-medium">{t("tokens.scopes")}</legend>
        {allowed.map((scope) => (
          <label key={scope} className="flex min-h-11 items-center gap-3 text-sm">
            <input type="checkbox" className="size-4 accent-[var(--primary)]" checked={scopes.includes(scope)}
              onChange={(e) => setScopes((now) => (e.target.checked ? allowed.filter((s) => now.includes(s) || s === scope) : now.filter((s) => s !== scope)))} />
            {t(`tokens.scope.${scope}`)}
          </label>
        ))}
      </fieldset>
      <fieldset className="space-y-1">
        <legend className="text-sm font-medium">{t("tokens.expires")}</legend>
        <div className="flex flex-wrap gap-2">
          {EXPIRIES.map((days) => {
            const value = days === null ? "never" : String(days);
            return (
              <label key={value} className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
                <input type="radio" name={expiryName} value={value} checked={expiry === value} onChange={() => setExpiry(value)} className="size-4 accent-[var(--primary)]" />
                {t(`tokens.expires.${value as "30" | "90" | "365" | "never"}`)}
              </label>
            );
          })}
        </div>
      </fieldset>
      {create.error ? <ErrorNotice message={error(isApiError(create.error) ? create.error.code : "INTERNAL")} /> : null}
      <Button type="submit" disabled={create.isPending || scopes.length === 0 || !name.trim()}>{t("tokens.create")}</Button>
    </form>
  );
}

function Secret({ created, onDone }: { created: CreatedToken; onDone: () => void }) {
  const { t } = useI18n();
  const copy = async () => {
    await navigator.clipboard.writeText(created.secret);
    toast(t("tokens.copied"));
  };
  return (
    <div className="space-y-3 rounded-lg border border-primary p-3" role="status">
      <h3 className="font-medium">{t("tokens.secret_title")}</h3>
      <p className="text-sm text-muted-foreground" id="secret-hint">{t(created.token.kind === "agent" ? "tokens.secret_hint_agent" : "tokens.secret_hint")}</p>
      <Label htmlFor="token-secret" className="sr-only">{t("tokens.secret_title")}</Label>
      <Input id="token-secret" readOnly value={created.secret} aria-describedby="secret-hint" className="font-mono"
        onFocus={(e) => e.currentTarget.select()} />
      <div className="flex flex-wrap gap-2">
        <Button onClick={copy} className="gap-2"><Copy aria-hidden />{t("tokens.copy")}</Button>
        <Button variant="outline" onClick={onDone}>{t("tokens.done")}</Button>
      </div>
    </div>
  );
}
