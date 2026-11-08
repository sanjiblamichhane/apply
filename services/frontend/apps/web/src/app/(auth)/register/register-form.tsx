"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label } from "@apply/ui";
import { View, ViewOff } from "@apply/ui/icons";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { readLocaleCookie } from "@/lib/locale";
import { useRegister, useSetup } from "@/lib/queries";

import { GlassPanel, ON_GLASS_FIELD } from "../glass-panel";

const MIN_PASSWORD = 12;

/**
 * Making an account: on the first run, the one that owns apply on this machine; after that, anyone's own,
 * while the owner keeps registration open (the API refuses otherwise, and this page says so and points to
 * sign-in). Each account sees only its own profiles, applications and documents.
 */
export function RegisterForm() {
  const { t, error: errorText } = useI18n();
  const router = useRouter();
  const setup = useSetup();
  const register = useRegister();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [demo, setDemo] = useState(false);
  const [tried, setTried] = useState(false);

  const mismatch = tried && confirm !== password;
  const tooShort = tried && password.length < MIN_PASSWORD;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setTried(true);
    if (password.length < MIN_PASSWORD || confirm !== password) return;
    try {
      await register.mutateAsync({ email, password, locale: readLocaleCookie() ?? "en", demo });
      // With the demo, straight to its applications; without, to making a first profile.
      router.replace(demo ? "/applications" : "/profiles/new");
    } catch {
      // Shown below, from register.error.
    }
  }

  const closed = setup.data?.open === false
    || isApiError(register.error, "OWNER_EXISTS") || isApiError(register.error, "REGISTRATION_CLOSED");
  const first = setup.data?.first_run ?? false;
  const title = t(first ? "auth.register.title" : "auth.create_account");
  const failure = register.error && !closed ? errorText(isApiError(register.error) ? register.error.code : "INTERNAL") : null;
  const signInLink = (
    <p className="text-sm text-muted-foreground">
      {t("auth.have_account")}{" "}
      <Link href="/sign-in" className="font-medium text-primary underline underline-offset-4">{t("auth.title")}</Link>
    </p>
  );

  if (closed) {
    return (
      <GlassPanel eyebrow={t("app.name")} title={title} intro={t("auth.register.closed")}>
        <Button asChild className="w-full"><Link href="/sign-in">{t("auth.title")}</Link></Button>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel eyebrow={t("app.name")} title={title} intro={t(first ? "auth.register.intro" : "auth.register.intro_member")}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {failure ? <ErrorNotice message={failure} /> : null}
        <div className="space-y-2">
          <Label htmlFor="email">{t("auth.email")}</Label>
          <Input id="email" type="email" autoComplete="username" required value={email} className={ON_GLASS_FIELD}
            onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">{t("auth.password")}</Label>
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
        {/* Off unless asked: a sample to look around in, never mixed into someone's data without their say. */}
        <div className="flex items-start gap-3">
          <input id="demo" type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)}
            className="mt-0.5 size-5 shrink-0 accent-[var(--primary)]" aria-describedby="demo-hint" />
          <div className="space-y-1">
            <Label htmlFor="demo">{t("auth.register.demo")}</Label>
            <p id="demo-hint" className="text-sm text-muted-foreground">{t("auth.register.demo_hint")}</p>
          </div>
        </div>
        <Button type="submit" className="w-full" disabled={register.isPending || !email || !password || !confirm}>
          {register.isPending ? t("auth.register.submitting") : t("auth.register.submit")}
        </Button>
        {signInLink}
      </form>
    </GlassPanel>
  );
}
