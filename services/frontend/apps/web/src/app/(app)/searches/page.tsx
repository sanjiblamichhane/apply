"use client";

import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import { Badge, Button } from "@apply/ui";
import { Add, Search } from "@apply/ui/icons";
import Link from "next/link";

import { Help } from "@/components/help";
import { useCurrentPack } from "@/lib/pack-choice";
import { useSearches } from "@/lib/discovery";

export default function SearchesPage() {
  const { t, error } = useI18n();
  const [currentPack] = useCurrentPack();
  const searches = useSearches();
  const add = <Button asChild className="gap-2"><Link href="/searches/new"><Add aria-hidden />{t("searches.new")}</Link></Button>;
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <title>{`${t("searches.title")} · apply`}</title>
      <PageHeader help={<Help slug="searches" />} title={t("searches.title")} description={t(forPack("searches.description", currentPack))} actions={add} />
      {searches.error ? <ErrorNotice message={error((searches.error as { code?: string }).code)} retryLabel={t("action.retry")} onRetry={() => searches.refetch()} /> : null}
      {searches.data?.length === 0 ? <EmptyState icon={Search} title={t("searches.empty.title")} body={t(forPack("searches.empty.body", currentPack))} action={add} /> : null}
      {searches.data && searches.data.length > 0 ? (
        <ul className="divide-y rounded-xl border bg-card">
          {searches.data.map((search) => {
            const c = search.criteria;
            const words = c.keywords ?? [];
            return (
              <li key={search.id} className="relative flex items-center gap-3 px-4 py-3 focus-within:ring-2 focus-within:ring-ring">
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    <Link href={`/searches/${search.id}`} className="after:absolute after:inset-0 focus-visible:outline-none">{search.name}</Link>
                  </p>
                  <p className="truncate text-sm text-muted-foreground">
                    {words.length === 0 ? t("searches.summary.everything")
                      : t(c.match_all ? "searches.summary.all" : "searches.summary.any", { words: words.join(", ") })}
                    {c.remote_only ? ` · ${t("searches.remote_only")}` : ""}
                  </p>
                </div>
                <Badge variant={search.enabled ? "success" : "muted"}>{search.enabled ? t("searches.enabled") : t("searches.paused")}</Badge>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
