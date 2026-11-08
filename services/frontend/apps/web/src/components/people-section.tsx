"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogTitle, AlertDialogTrigger, Badge, Button, buttonVariants,
} from "@apply/ui";
import { Trash } from "@apply/ui/icons";
import { useId, useState } from "react";
import { toast } from "sonner";

import { useDeletePerson, usePeople, useRegistration, useSetRegistration, useTurnPerson } from "@/lib/people";
import { useMe } from "@/lib/queries";

/**
 * Settings → People, for the owner only: whether anyone may create an account, and who has one. Turning an
 * account off is undone by turning it on; deleting can't be undone, so it's the one thing asked first.
 */
export function PeopleSection() {
  const { t, error, date, relative } = useI18n();
  const me = useMe();
  const owner = me.data?.is_owner ?? false;
  const people = usePeople(owner);
  const registration = useRegistration(owner);
  const setRegistration = useSetRegistration();
  const turn = useTurnPerson();
  const remove = useDeletePerson();
  const id = useId();
  // The switch moves the moment it's pressed, and settles on what was saved (back, if saving failed).
  const [pressed, setPressed] = useState<boolean | null>(null);
  if (!owner) return null;
  const failure = people.error ?? registration.error ?? setRegistration.error ?? turn.error ?? remove.error;

  return (
    <section aria-labelledby="people-heading" className="space-y-3 rounded-xl border bg-card p-4">
      <h2 id="people-heading" className="text-lg font-semibold">{t("people.title")}</h2>
      <p className="text-sm text-muted-foreground">{t("people.hint")}</p>
      {failure ? <ErrorNotice message={error(isApiError(failure) ? failure.code : "INTERNAL")} /> : null}

      {registration.data ? (
        <label className="flex min-h-11 cursor-pointer items-start gap-3 text-sm">
          <input type="checkbox" role="switch" checked={pressed ?? registration.data.open}
            onChange={(e) => {
              setPressed(e.target.checked);
              setRegistration.mutate(e.target.checked, { onSettled: () => setPressed(null) });
            }} aria-describedby={`${id}-registration`}
            className="mt-0.5 size-5 shrink-0 accent-[var(--primary)]" />
          <span>
            <span className="font-medium">{t("people.registration")}</span>
            <span id={`${id}-registration`} className="block text-muted-foreground">{t("people.registration_hint")}</span>
          </span>
        </label>
      ) : null}

      <ul className="divide-y">
        {(people.data ?? []).map((person) => (
          <li key={person.id} className="flex flex-wrap items-center gap-3 py-3">
            <div className="min-w-0 flex-1 space-y-0.5">
              <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                <span className="truncate">{person.email}</span>
                {person.is_owner ? <Badge variant="secondary">{t("people.you")}</Badge> : null}
                {person.disabled_at ? <Badge variant="outline">{t("people.off")}</Badge> : null}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("people.joined", { when: date(person.created_at, { dateStyle: "medium" }) })} ·{" "}
                {person.last_sign_in_at ? t("people.last_sign_in", { when: relative(person.last_sign_in_at) }) : t("people.never_signed_in")}
              </p>
            </div>
            {person.is_owner ? null : (
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={turn.isPending}
                  onClick={() => turn.mutate({ id: person.id, on: Boolean(person.disabled_at) })}>
                  {t(person.disabled_at ? "people.turn_on" : "people.turn_off")}<span className="sr-only">: {person.email}</span>
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button size="sm" variant="ghost" className="gap-2">
                      <Trash aria-hidden />{t("action.delete")}<span className="sr-only">: {person.email}</span>
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogTitle>{t("people.delete_title", { email: person.email })}</AlertDialogTitle>
                    <AlertDialogDescription>{t("people.delete_body")}</AlertDialogDescription>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{t("action.cancel")}</AlertDialogCancel>
                      <AlertDialogAction className={buttonVariants({ variant: "destructive" })}
                        onClick={() => remove.mutate(person.id, { onSuccess: () => toast(t("people.deleted", { email: person.email })) })}>
                        {t("action.delete")}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
