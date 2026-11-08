"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label } from "@apply/ui";
import { View, ViewOff } from "@apply/ui/icons";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { useResetFor, useResetPassword } from "@/lib/queries";

import { GlassPanel, ON_GLASS_FIELD } from "../glass-panel";

const MIN_PASSWORD = 12;

/**
 * A new password from an emailed link. The token is read from the address once, then taken out of it (and so
 * out of this browser's history). A used or expired link says so and offers a new one. After the change every
 * session of the account has ended, so it's back to sign-in, which says the password changed.
 */
export function ResetForm() {
  const { t, error: errorText } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const [token] = useState(() => params.get("token"));
  const target = useResetFor(token);
  const reset = useResetPassword();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [tried, setTried] = useState(false);

  useEffect(() => {
    if (token) window.history.replaceState(null, "", "/reset-password");
  }, [token]);

  const mismatch = tried && confirm !== password;
  const tooShort = tried && password.length < MIN_PASSWORD;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setTried(true);
    if (!token || password.length < MIN_PASSWORD || confirm !== password) return;
    try {
      await reset.mutateAsync({ token, password });
      router.replace("/sign-in?reset=done");
    } catch {
      // Shown below, from reset.error.
    }
  }

  const invalid = !token || isApiError(target.error, "RESET_LINK_INVALID") || isApiError(reset.error, "RESET_LINK_INVALID");
  if (invalid) {
    return (
      <GlassPanel eyebrow={t("app.name")} title={t("auth.reset.invalid_title")} intro={t("auth.reset.invalid")}>
        <div className="space-y-4">
          <Button asChild className="w-full"><Link href="/forgot-password">{t("auth.reset.new_link")}</Link></Button>
          <p className="text-sm">
            <Link href="/sign-in" className="font-medium text-primary underline underline-offset-4">{t("auth.back_to_sign_in")}</Link>
          </p>
        </div>
      </GlassPanel>
    );
  }

  if (!target.data) {
    return (
      <GlassPanel eyebrow={t("app.name")} title={t("auth.reset.title")} intro={t("auth.reset.checking")}>
        {target.error ? (
          <ErrorNotice message={errorText(isApiError(target.error) ? target.error.code : "INTERNAL")}
            retryLabel={t("action.retry")} onRetry={() => target.refetch()} />
        ) : null}
      </GlassPanel>
    );
  }

  const failure = reset.error ? errorText(isApiError(reset.error) ? reset.error.code : "INTERNAL") : null;

  return (
    <GlassPanel eyebrow={t("app.name")} title={t("auth.reset.title")} intro={t("auth.reset.intro", { email: target.data.email })}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {failure ? <ErrorNotice message={failure} /> : null}
        {/* For a password manager: which account this new password is for. */}
        <input type="email" name="username" autoComplete="username" value={target.data.email} readOnly hidden />
        <div className="space-y-2">
          <Label htmlFor="password">{t("auth.reset.password")}</Label>
          <p id="password-hint" className={tooShort ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
            {t("auth.register.password_hint")}
          </p>
          <div className="relative">
            <Input id="password" type={show ? "text" : "password"} autoComplete="new-password" required minLength={MIN_PASSWORD}
              value={password} onChange={(e) => setPassword(e.target.value)} className={`pe-12 ${ON_GLASS_FIELD}`}
              aria-describedby="password-hint" aria-invalid={tooShort || undefined} />
            <Button type="button" variant="ghost" size="icon" className="absolute end-0 top-0"
              aria-label={show ? t("auth.hide_password") : t("auth.show_password")} aria-pressed={show}
              onClick={() => setShow((v) => !v)}>
              {show ? <ViewOff aria-hidden /> : <View aria-hidden />}
            </Button>
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm">{t("auth.register.confirm")}</Label>
          <Input id="confirm" type={show ? "text" : "password"} autoComplete="new-password" required value={confirm}
            className={ON_GLASS_FIELD} onChange={(e) => setConfirm(e.target.value)}
            aria-describedby={mismatch ? "confirm-error" : undefined} aria-invalid={mismatch || undefined} />
          {mismatch ? <p id="confirm-error" className="text-sm text-destructive">{t("auth.register.mismatch")}</p> : null}
        </div>
        <Button type="submit" className="w-full" disabled={reset.isPending || !password || !confirm}>
          {reset.isPending ? t("auth.reset.submitting") : t("auth.reset.submit")}
        </Button>
      </form>
    </GlassPanel>
  );
}
