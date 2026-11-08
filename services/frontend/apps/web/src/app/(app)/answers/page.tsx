"use client";

import { type Answer, isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice, PageHeader } from "@apply/kit";
import { Badge, Button, Input, Label } from "@apply/ui";
import { Add, Information, Trash, ViewOff } from "@apply/ui/icons";
import { type FormEvent, useEffect, useId, useState } from "react";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { useAddDefaultAnswers, useAnswers, useCreateAnswer, useDeleteAnswer, useUpdateAnswer } from "@/lib/review";

export default function AnswersPage() {
  const { t, error } = useI18n();
  const answers = useAnswers();
  const defaults = useAddDefaultAnswers();
  const ask = defaults.mutate;
  const empty = answers.isSuccess && answers.data.length === 0;
  // The common questions are there from the start: nobody should have to type "Are you allowed to work here?".
  useEffect(() => {
    if (empty) ask();
  }, [empty, ask]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${t("answers.title")} · apply`}</title>
      <PageHeader help={<Help slug="answers" />} title={t("answers.title")} description={t("answers.description")} />
      <p className="flex items-start gap-2 rounded-lg border p-3 text-sm"><Information className="mt-0.5 size-4 shrink-0" aria-hidden />{t("answers.sensitive_note")}</p>
      {answers.error ? <ErrorNotice message={error(isApiError(answers.error) ? answers.error.code : "INTERNAL")} /> : null}
      <ul className="space-y-3">
        {(answers.data ?? []).map((answer) => <li key={answer.id}><AnswerRow answer={answer} /></li>)}
      </ul>
      <NewAnswer />
    </div>
  );
}

function AnswerRow({ answer }: { answer: Answer }) {
  const { t, pick, locale, error } = useI18n();
  const update = useUpdateAnswer();
  const remove = useDeleteAnswer();
  const [value, setValue] = useState(answer.answer);
  const id = useId();
  const question = pick(answer.question);

  function save(next: string) {
    setValue(next);
    update.mutate({ id: answer.id, answer: next }, {
      onSuccess: () => toast(t("answers.saved")),
      onError: (e) => toast.error(error(isApiError(e) ? e.code : "INTERNAL")),
    });
  }

  return (
    <div className="space-y-2 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p id={`${id}-q`} className="font-medium">{question}</p>
        {answer.is_sensitive ? <Badge variant="muted"><ViewOff className="size-3" aria-hidden />{t("answers.private")}</Badge> : null}
      </div>
      {answer.answer_type === "yes_no" ? (
        <fieldset aria-labelledby={`${id}-q`} className="flex gap-2">
          {(["yes", "no"] as const).map((option) => (
            <label key={option} className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring">
              <input type="radio" name={id} value={option} checked={value === option} onChange={() => save(option)} className="size-4 accent-[var(--primary)]" />
              {t(`answers.${option}`)}
            </label>
          ))}
        </fieldset>
      ) : answer.answer_type === "choice" ? (
        <select aria-labelledby={`${id}-q`} value={value} onChange={(e) => save(e.target.value)}
          className="flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm">
          {answer.choices.map((c) => <option key={c.value} value={c.value}>{c.label[locale] || c.label.en}</option>)}
        </select>
      ) : (
        <form className="flex flex-col gap-2 sm:flex-row" onSubmit={(e) => { e.preventDefault(); save(value); }}>
          <Label htmlFor={`${id}-a`} className="sr-only">{question}</Label>
          <Input id={`${id}-a`} type={answer.answer_type === "url" ? "url" : "text"} value={value} placeholder={t("answers.unanswered")}
            onChange={(e) => setValue(e.target.value)} className="flex-1" />
          <Button type="submit" variant="outline" disabled={value === answer.answer || update.isPending}>{t("action.save")}</Button>
        </form>
      )}
      {answer.source === "user" ? (
        <Button size="sm" variant="ghost" className="gap-2" onClick={() => remove.mutate(answer.id)}><Trash aria-hidden />{t("action.remove")}<span className="sr-only">: {question}</span></Button>
      ) : null}
    </div>
  );
}

function NewAnswer() {
  const { t, error } = useI18n();
  const create = useCreateAnswer();
  const [question, setQuestion] = useState("");
  const [key, setKey] = useState("");
  const [answer, setAnswer] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ key, question: { en: question }, answer }, {
      onSuccess: () => {
        setQuestion(""); setKey(""); setAnswer("");
        toast(t("answers.saved"));
      },
    });
  }
  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border bg-card p-4">
      <h2 className="text-lg font-semibold">{t("answers.add")}</h2>
      {create.error ? <ErrorNotice message={error(isApiError(create.error) ? create.error.code : "INTERNAL")} /> : null}
      <div className="space-y-1">
        <Label htmlFor="new-question">{t("answers.question")}</Label>
        <Input id="new-question" value={question} onChange={(e) => {
          setQuestion(e.target.value);
          setKey(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").replace(/^(\d)/, "q_$1").slice(0, 40));
        }} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="new-key">{t("answers.key")}</Label>
        <p id="new-key-hint" className="text-sm text-muted-foreground">{t("answers.key_hint")}</p>
        <Input id="new-key" value={key} onChange={(e) => setKey(e.target.value)} aria-describedby="new-key-hint" />
      </div>
      <div className="space-y-1">
        <Label htmlFor="new-answer">{t("answers.answer")}</Label>
        <Input id="new-answer" value={answer} onChange={(e) => setAnswer(e.target.value)} />
      </div>
      <Button type="submit" className="gap-2" disabled={!question.trim() || !/^[a-z][a-z0-9_]*$/.test(key) || create.isPending}><Add aria-hidden />{t("answers.add")}</Button>
    </form>
  );
}
