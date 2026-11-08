"use client";

import { useI18n } from "@apply/i18n/react";
import { EmptyState, ErrorNotice, PageHeader } from "@apply/kit";
import { Badge, Button } from "@apply/ui";
import { Add, StarFilled, User } from "@apply/ui/icons";
import Link from "next/link";

import { Help } from "@/components/help";
import { useProfiles } from "@/lib/queries";

export default function ProfilesPage() {
  const { t, error, relative } = useI18n();
  const profiles = useProfiles();
  const newButton = (
    <Button asChild className="gap-2"><Link href="/profiles/new"><Add aria-hidden />{t("profiles.new")}</Link></Button>
  );
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <title>{`${t("profiles.title")} · apply`}</title>
      <PageHeader help={<Help slug="profiles" />} title={t("profiles.title")} description={t("profiles.description")} actions={newButton} />
      {profiles.error ? <ErrorNotice message={error((profiles.error as { code?: string }).code)} retryLabel={t("action.retry")} onRetry={() => profiles.refetch()} /> : null}
      {profiles.data?.length === 0 ? (
        <EmptyState icon={User} title={t("profiles.empty.title")} body={t("profiles.empty.body")} action={newButton} />
      ) : null}
      {profiles.data && profiles.data.length > 0 ? (
        <ul className="divide-y rounded-xl border bg-card">
          {profiles.data.map((profile) => (
            <li key={profile.id} className="relative flex items-center gap-3 px-4 py-3 focus-within:ring-2 focus-within:ring-ring">
              <div className="min-w-0 flex-1">
                <p className="font-medium">
                  <Link href={`/profiles/${profile.id}`} className="after:absolute after:inset-0 focus-visible:outline-none">{profile.name}</Link>
                </p>
                <p className="truncate text-sm text-muted-foreground">
                  {String((profile.attributes as Record<string, unknown>).full_name ?? "") || profile.summary}
                  {" · "}<time dateTime={profile.updated_at}>{relative(profile.updated_at)}</time>
                </p>
              </div>
              {profile.reading?.status === "pending" ? <Badge variant="muted">{t("profiles.reading.badge")}</Badge> : null}
              {profile.is_default ? <Badge variant="muted"><StarFilled className="size-3" aria-hidden />{t("profiles.default")}</Badge> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {profiles.isLoading ? <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p> : null}
    </div>
  );
}
