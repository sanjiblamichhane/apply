"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label } from "@apply/ui";
import { View, ViewOff } from "@apply/ui/icons";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { readLocaleCookie } from "@/lib/locale";
import { useSetup, useSignIn, useUpdateMe } from "@/lib/queries";

import { useLocaleControl } from "../../providers";
import { GlassPanel, ON_GLASS_FIELD } from "../glass-panel";

/** Only a path on this site: never send someone to another site after signing in (open redirect). */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/today";
}

export function SignInForm() {
  const { t, error: errorText } = useI18n();
  const setup = useSetup();
  const updateMe = useUpdateMe();
  const router = useRouter();
  const params = useSearchParams();
  const signIn = useSignIn();
  const { setLocale } = useLocaleControl();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const me = await signIn.mutateAsync({ email, password });
      // This page is always English. A language chosen on this device before (in Settings) wins, and the
      // account remembers it; a device with no choice yet takes the account's.
      const chosen = readLocaleCookie();
      if (chosen) {
        if (me.locale !== chosen) updateMe.mutate({ locale: chosen });
      } else {
        setLocale(me.locale);
      }
      router.replace(safeNext(params.get("next")));
    } catch {
      // Shown below, from signIn.error.
    }
  }

  const failure = signIn.error;
  const message = !failure ? null : isApiError(failure, "SIGN_IN_LOCKED")
    ? t("auth.locked", { minutes: Math.max(1, Math.ceil((failure.problem?.retry_after ?? 60) / 60)) })
    : errorText(isApiError(failure) ? failure.code : "INTERNAL");

  return (
    <GlassPanel eyebrow={t("app.name")} title={t("auth.title")} intro={t("auth.intro")}>
        <form onSubmit={submit} className="space-y-4" noValidate>
          {message ? <ErrorNotice message={message} /> : null}
          {!message && params.get("reset") === "done" ? (
            <p role="status" className="rounded-lg border border-border bg-background/90 px-4 py-3 text-sm">
              {t("auth.reset.done")}
            </p>
          ) : null}
          <div className="space-y-2">
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input id="email" className={ON_GLASS_FIELD} type="email" autoComplete="username" required value={email}
              onChange={(e) => setEmail(e.target.value)} aria-invalid={Boolean(failure) || undefined} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <div className="relative">
              <Input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" required
                value={password} onChange={(e) => setPassword(e.target.value)} className={`pe-12 ${ON_GLASS_FIELD}`}
                aria-invalid={Boolean(failure) || undefined} />
              <Button type="button" variant="ghost" size="icon" className="absolute end-0 top-0"
                aria-label={showPassword ? t("auth.hide_password") : t("auth.show_password")}
                aria-pressed={showPassword} onClick={() => setShowPassword((v) => !v)}>
                {showPassword ? <ViewOff aria-hidden /> : <View aria-hidden />}
              </Button>
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={signIn.isPending || !email || !password}>
            {signIn.isPending ? t("auth.submitting") : t("auth.submit")}
          </Button>
          <p className="text-sm">
            <Link href="/forgot-password" className="font-medium text-primary underline underline-offset-4">
              {t("auth.forgot_link")}
            </Link>
          </p>
          {setup.data?.open ? (
            <p className="text-sm text-muted-foreground">
              {t(setup.data.first_run ? "auth.first_run" : "auth.new_here")}{" "}
              <Link href="/register" className="font-medium text-primary underline underline-offset-4">
                {t(setup.data.first_run ? "auth.create_link" : "auth.create_account")}
              </Link>
            </p>
          ) : null}
        </form>
    </GlassPanel>
  );
}
