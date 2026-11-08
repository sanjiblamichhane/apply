/**
 * What Fill would put in the form, before anything is written (the content script's preview: plan() read only).
 * Three lists: what apply will fill, each with a tick the person can take off; what's left for them, and why; and
 * what's already filled, which stays (folded). The fill only writes the ticked fields.
 */
import type { PreviewRow } from "@apply/ats-adapters";
import { useI18n } from "@apply/i18n/react";
import { ChevronDown } from "@apply/ui/icons";
import { useState } from "react";

export const FILLS: PreviewRow["status"][] = ["fill", "check", "attach"];

export function Preview({ rows, skipped, onToggle, busy }: {
  rows: PreviewRow[]; skipped: ReadonlySet<string>; onToggle: (key: string) => void; busy: boolean;
}) {
  const { t } = useI18n();
  const fills = rows.filter((r) => FILLS.includes(r.status));
  const left = rows.filter((r) => r.status === "pick" || r.status === "blank")
    .sort((a, b) => Number(b.required) - Number(a.required));
  const kept = rows.filter((r) => r.status === "kept");
  const ticked = fills.filter((r) => !skipped.has(r.key)).length;
  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-2" aria-labelledby="preview-fill">
        <h2 id="preview-fill" className="text-base font-semibold">{t("ext.preview.title", { count: ticked })}</h2>
        {fills.length === 0 ? <p className="text-sm text-muted-foreground">{t("ext.preview.none")}</p> : (
          <>
            <p className="text-sm text-muted-foreground">{t("ext.preview.hint")}</p>
            <ul className="flex flex-col divide-y rounded-md border">
              {fills.map((row) => (
                <FillRow key={row.key} row={row} on={!skipped.has(row.key)} onToggle={() => onToggle(row.key)} busy={busy} />
              ))}
            </ul>
          </>
        )}
      </section>
      {left.length > 0 && (
        <section className="flex flex-col gap-2" aria-labelledby="preview-left">
          <h2 id="preview-left" className="text-base font-semibold">{t("ext.left_for_you")}</h2>
          <ul className="flex flex-col divide-y rounded-md border">
            {left.map((row) => (
              <li key={row.key} className="flex flex-col gap-0.5 px-3 py-2">
                <p className="text-sm font-medium">
                  {row.label || "—"}{row.required && <span className="text-muted-foreground"> · {t("ext.required")}</span>}
                </p>
                {row.status === "pick" ? (
                  <>
                    <p className="text-sm text-muted-foreground">{t("ext.reason.custom")}</p>
                    {row.value && <Value row={row} prefix={(v) => t("ext.suggestion", { answer: v })} />}
                  </>
                ) : <p className="text-sm text-muted-foreground">{t(`ext.reason.${row.reason ?? "unknown"}`)}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {kept.length > 0 && <Kept rows={kept} />}
    </div>
  );
}

function FillRow({ row, on, onToggle, busy }: { row: PreviewRow; on: boolean; onToggle: () => void; busy: boolean }) {
  const { t } = useI18n();
  const id = `preview-${row.key}`;
  return (
    <li className="flex items-start gap-3 px-3 py-2">
      <input id={id} type="checkbox" checked={on} onChange={onToggle} disabled={busy}
        className="mt-0.5 size-5 shrink-0 accent-[var(--primary)]" aria-describedby={`${id}-value`} />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <label htmlFor={id} className={`text-sm font-medium ${on ? "" : "text-muted-foreground line-through"}`}>
          {row.label || "—"}{row.required && <span className="font-normal text-muted-foreground"> · {t("ext.required")}</span>}
        </label>
        <div id={`${id}-value`}>
          {row.status === "check" ? <p className="text-sm text-muted-foreground">{t("ext.preview.ticked")}</p> : <Value row={row} />}
        </div>
      </div>
    </li>
  );
}

/** A value, shown in full (wrapping); an equal-opportunity answer stays hidden until asked for. */
function Value({ row, prefix }: { row: PreviewRow; prefix?: (value: string) => string }) {
  const { t } = useI18n();
  const [shown, setShown] = useState(false);
  const value = row.value ?? "";
  if (row.sensitive && !shown) {
    return (
      <p className="flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
        {t("ext.preview.hidden")}
        <button type="button" onClick={() => setShown(true)}
          className="min-h-6 font-medium text-primary underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring">
          {t("ext.copy.show")}
        </button>
      </p>
    );
  }
  return (
    <p className="whitespace-pre-line break-words text-sm text-muted-foreground">
      {prefix ? prefix(value) : value}
      {row.sensitive && (
        <button type="button" onClick={() => setShown(false)}
          className="ms-2 min-h-6 font-medium text-primary underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring">
          {t("ext.preview.hide")}
        </button>
      )}
    </p>
  );
}

/** What the person (or an earlier fill) already put in: folded, since it stays as it is. */
function Kept({ rows }: { rows: PreviewRow[] }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-base font-semibold">
        <button type="button" aria-expanded={open} aria-controls="preview-kept" onClick={() => setOpen(!open)}
          className="-mx-1 flex min-h-11 w-full items-center gap-1 rounded-md px-1 text-start hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring">
          <ChevronDown aria-hidden className={`size-4 shrink-0 transition-transform motion-reduce:transition-none ${open ? "" : "-rotate-90"}`} />
          {t("ext.preview.kept", { count: rows.length })}
        </button>
      </h2>
      {open && (
        <div id="preview-kept" className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">{t("ext.preview.kept_hint")}</p>
          <ul className="flex flex-col divide-y rounded-md border">
            {rows.map((row) => <li key={row.key} className="px-3 py-2 text-sm">{row.label || "—"}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}
