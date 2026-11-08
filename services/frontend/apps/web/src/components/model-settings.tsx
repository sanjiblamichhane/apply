"use client";

/**
 * Settings → Model: the models found on this computer's local model servers, grouped by server.
 * Choose one, and optionally a writing model on the same server; "Test and use" tests it first and keeps the current
 * one if it can't answer. "Use the settings (.env)" goes back.
 */
import { type FoundModel, isApiError, type ModelServer } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { Button, Input } from "@apply/ui";
import { CheckmarkFilled, Renew, WarningAlt } from "@apply/ui/icons";
import { useId, useState } from "react";
import { toast } from "sonner";

import { useChooseModel, useMe, useModels, useModelStatus, useResetModel } from "@/lib/queries";

interface Option {
  server: ModelServer;
  model: FoundModel;
  key: string;
}

const keyOf = (baseUrl: string, model: string) => `${baseUrl}\n${model}`;
const hostOf = (baseUrl: string) => baseUrl.replace(/^https?:\/\//, "");
const SELECT = "flex min-h-11 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm";

export function ModelSection() {
  const { t, error } = useI18n();
  const found = useModels();
  const status = useModelStatus();
  const choose = useChooseModel();
  const reset = useResetModel();
  const me = useMe();
  // The model is the install's, shared by every account: only its owner changes it.
  const owner = me.data?.is_owner ?? false;
  const id = useId();
  const [picked, setPicked] = useState<string | null>(null);
  const [writing, setWriting] = useState<string | null>(null);
  const [context, setContext] = useState<string | null>(null);

  const current = found.data?.current;
  const servers = found.data?.endpoints ?? [];
  const options: Option[] = servers.flatMap((server) =>
    server.models.map((model) => ({ server, model, key: keyOf(server.base_url, model.name) })));
  const usable = options.filter((o) => o.model.usable);
  const currentKey = current ? keyOf(current.base_url, current.model) : "";
  const selectedKey = picked ?? (usable.some((o) => o.key === currentKey) ? currentKey : usable[0]?.key ?? "");
  const selected = usable.find((o) => o.key === selectedKey);
  const sameServer = usable.filter((o) => o.server.base_url === selected?.server.base_url && o.key !== selectedKey);
  const writingName = writing
    ?? (current && selected && current.base_url === selected.server.base_url ? current.writing_model : "");
  const writingValue = sameServer.some((o) => o.model.name === writingName) ? writingName : "";
  const native = selected?.server.api === "native";
  const contextValue = context ?? String(current?.num_ctx ?? 16384);
  const contextNumber = Number(contextValue);
  const contextValid = !native || (Number.isInteger(contextNumber) && contextNumber >= 2048 && contextNumber <= 262144);
  const unchanged = selected?.key === currentKey && writingValue === (current?.writing_model ?? "")
    && (!native || contextNumber === current?.num_ctx) && current?.source === "chosen";

  const size = (m: FoundModel) => (m.size_bytes ? t("settings.model.gb", { size: Math.round(m.size_bytes / 1e8) / 10 }) : null);
  const label = (m: FoundModel) => [m.name, m.parameters, size(m), m.loaded ? t("settings.model.loaded") : null,
    m.usable ? null : t("settings.model.embedding")].filter(Boolean).join(" · ");

  function use() {
    if (!selected) return;
    choose.mutate(
      {
        base_url: selected.server.base_url,
        model: selected.model.name,
        writing_model: writingValue,
        num_ctx: native ? contextNumber : null,
      },
      {
        onSuccess: (done) => {
          setPicked(null); setWriting(null); setContext(null);
          toast(t("settings.model.used", { model: done.current.model, seconds: Math.round(done.milliseconds / 100) / 10 }));
        },
      },
    );
  }

  const failure = choose.error;
  const reason = isApiError(failure) ? (failure.problem as { reason?: string } | null)?.reason : undefined;
  const st = status.data;

  return (
    <section aria-labelledby="model-heading" className="space-y-4 rounded-xl border bg-card p-4">
      <h2 id="model-heading" className="text-lg font-semibold">{t("settings.model")}</h2>
      <p className="text-sm text-muted-foreground">{t("settings.model.hint")}</p>

      <div aria-live="polite" className="space-y-1">
        {current ? (
          <p className="flex items-start gap-2 text-sm">
            {st ? (st.ready ? <CheckmarkFilled className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
              : <WarningAlt className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />) : null}
            <span>
              <span className="font-medium">{t("settings.model.in_use", { model: current.model, server: hostOf(current.base_url) })}</span>{" "}
              {t(current.source === "chosen" ? "settings.model.source.chosen" : "settings.model.source.settings")}
              {current.writing_model ? <> {t("settings.model.in_use_writing", { model: current.writing_model })}</> : null}
            </span>
          </p>
        ) : null}
        {st && !st.ready ? (
          <p className="text-sm">
            {st.reachable ? t("settings.model.missing", { models: st.missing.join(", ") }) : t("settings.model.unreachable", { url: st.base_url })}
          </p>
        ) : null}
        {found.isFetching ? <p role="status" className="text-sm text-muted-foreground">{t("settings.model.looking")}</p> : null}
      </div>

      {found.isSuccess && usable.length === 0 ? (
        <p className="rounded-lg border border-dashed p-3 text-sm">{t("settings.model.none")}</p>
      ) : null}

      {!owner && me.data ? <p className="text-sm text-muted-foreground">{t("settings.model.owner_only")}</p> : null}

      {owner && usable.length ? (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); use(); }}>
          <div className="space-y-1">
            <label htmlFor={`${id}-model`} className="text-sm font-medium">{t("settings.model.choose")}</label>
            <select id={`${id}-model`} value={selectedKey} aria-describedby={`${id}-model-hint`} className={SELECT}
              onChange={(e) => { setPicked(e.target.value); setWriting(null); }}>
              {servers.map((server) => (
                <optgroup key={server.base_url} label={`${t("settings.model.server")} · ${hostOf(server.base_url)}`}>
                  {server.models.map((m) => (
                    <option key={m.name} value={keyOf(server.base_url, m.name)} disabled={!m.usable}>{label(m)}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            <p id={`${id}-model-hint`} className="text-sm text-muted-foreground">{t("settings.model.choose_hint")}</p>
          </div>

          {selected ? <Facts model={selected.model} label={t("settings.model.about", { model: selected.model.name })} /> : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label htmlFor={`${id}-writing`} className="text-sm font-medium">{t("settings.model.writing")}</label>
              <select id={`${id}-writing`} value={writingValue} aria-describedby={`${id}-writing-hint`} className={SELECT}
                onChange={(e) => setWriting(e.target.value)}>
                <option value="">{t("settings.model.writing_same")}</option>
                {sameServer.map((o) => <option key={o.key} value={o.model.name}>{label(o.model)}</option>)}
              </select>
              <p id={`${id}-writing-hint`} className="text-sm text-muted-foreground">{t("settings.model.writing_hint")}</p>
            </div>
            {native ? (
              <div className="space-y-1">
                <label htmlFor={`${id}-context`} className="text-sm font-medium">{t("settings.model.context_label")}</label>
                <Input id={`${id}-context`} type="number" inputMode="numeric" min={2048} max={262144} step={1024}
                  value={contextValue} onChange={(e) => setContext(e.target.value)} aria-invalid={!contextValid}
                  aria-describedby={`${id}-context-hint`} />
                <p id={`${id}-context-hint`} className="text-sm text-muted-foreground">
                  {selected?.model.context_length
                    ? t("settings.model.context_hint", { max: selected.model.context_length })
                    : t("settings.model.context_hint_plain")}
                </p>
              </div>
            ) : null}
          </div>

          {choose.isPending ? (
            <p role="status" className="text-sm">{t("settings.model.testing", { model: selected?.model.name ?? "" })}</p>
          ) : null}
          {failure && !choose.isPending ? (
            <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
              <WarningAlt className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{error(isApiError(failure) ? failure.code : "NETWORK")}{reason ? ` ${error(reason)}` : ""}</span>
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={!selected || !contextValid || choose.isPending || unchanged}>{t("settings.model.use")}</Button>
            {current?.source === "chosen" ? (
              <Button type="button" variant="outline" disabled={reset.isPending}
                onClick={() => reset.mutate(undefined, { onSuccess: () => { choose.reset(); toast(t("settings.model.reset_done")); } })}>
                {t("settings.model.reset")}
              </Button>
            ) : null}
          </div>
        </form>
      ) : null}

      <Button variant="outline" size="sm" className="gap-2" disabled={found.isFetching || status.isFetching}
        onClick={() => { void found.refetch(); void status.refetch(); }}>
        <Renew aria-hidden />{t("settings.model.look_again")}
      </Button>
    </section>
  );
}

function Facts({ model, label }: { model: FoundModel; label: string }) {
  const { t } = useI18n();
  const rows: [string, string | null][] = [
    ["settings.model.fact.parameters", model.parameters],
    ["settings.model.fact.size", model.size_bytes ? t("settings.model.gb", { size: Math.round(model.size_bytes / 1e8) / 10 }) : null],
    ["settings.model.fact.context", model.context_length ? t("settings.model.context", { num_ctx: model.context_length }) : null],
    ["settings.model.fact.quantization", model.quantization],
    ["settings.model.fact.family", model.family],
    ["settings.model.fact.memory", t(model.loaded ? "settings.model.state.loaded" : "settings.model.state.cold")],
  ];
  return (
    <dl aria-label={label} className="grid gap-x-6 gap-y-2 rounded-lg border p-3 text-sm sm:grid-cols-3">
      {rows.filter(([, value]) => value).map(([key, value]) => (
        <div key={key}>
          <dt className="text-muted-foreground">{t(key as Parameters<typeof t>[0])}</dt>
          <dd className="font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
