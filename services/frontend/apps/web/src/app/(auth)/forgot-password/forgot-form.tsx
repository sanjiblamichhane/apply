"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { Button, Input, Label } from "@apply/ui";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { useForgotPassword, useSetup } from "@/lib/queries";

import { GlassPanel, ON_GLASS_FIELD } from "../glass-panel";

/**
 * "Forgot your password?": an email, then "Check your email". What's said after is the same whether or not
 * there's an account (the API answers the same too), so this page never tells anyone who has one.
 */
export function ForgotForm() {
  const { t, error: errorText } = useI18n();
  const setup = useSetup();
  const forgot = useForgotPassword();
  const [email, setEmail] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    try {
      await forgot.mutateAsync(email.trim());
      setSentTo(email.trim());
    } catch {
      // Shown below, from forgot.error.
    }
  }

  const backLink = (
    <p className="text-sm">
      <Link href="/sign-in" className="font-medium text-primary underline underline-offset-4">{t("auth.back_to_sign_in")}</Link>
    </p>
  );

  if (setup.data?.mail === false || isApiError(forgot.error, "MAIL_NOT_SET_UP")) {
    return (
      <GlassPanel eyebrow={t("app.name")} title={t("auth.forgot.title")} intro={t("auth.forgot.no_mail")}>
        <Button asChild className="w-full"><Link href="/sign-in">{t("auth.back_to_sign_in")}</Link></Button>
      </GlassPanel>
    );
  }

  const failure = forgot.error ? errorText(isApiError(forgot.error) ? forgot.error.code : "INTERNAL") : null;

  if (sentTo) {
    return (
      <GlassPanel eyebrow={t("app.name")} title={t("auth.forgot.sent_title")} intro={t("auth.forgot.sent", { email: sentTo })}>
        <div className="space-y-4">
          {failure ? <ErrorNotice message={failure} /> : null}
          <p className="text-sm text-muted-foreground">{t("auth.forgot.spam")}</p>
          <Button type="button" variant="outline" className="w-full" disabled={forgot.isPending} onClick={() => send()}>
            {forgot.isPending ? t("auth.forgot.submitting") : t("auth.forgot.again")}
          </Button>
          {backLink}
        </div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel eyebrow={t("app.name")} title={t("auth.forgot.title")} intro={t("auth.forgot.intro")}>
      <form onSubmit={send} className="space-y-4" noValidate>
        {failure ? <ErrorNotice message={failure} /> : null}
        <div className="space-y-2">
          <Label htmlFor="email">{t("auth.email")}</Label>
          <Input id="email" type="email" autoComplete="username" required value={email} className={ON_GLASS_FIELD}
            onChange={(e) => setEmail(e.target.value)} />
        </div>
        <Button type="submit" className="w-full" disabled={forgot.isPending || !email.trim()}>
          {forgot.isPending ? t("auth.forgot.submitting") : t("auth.forgot.submit")}
        </Button>
        {backLink}
      </form>
    </GlassPanel>
  );
}
