"use client";

import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { PageHeader } from "@apply/kit";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { useCurrentPack } from "@/lib/pack-choice";
import { SearchForm } from "@/components/search-form";
import { useSaveSearch } from "@/lib/discovery";

export default function NewSearchPage() {
  const { t } = useI18n();
  const [currentPack] = useCurrentPack();
  const router = useRouter();
  const save = useSaveSearch();
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${t("searches.new")} · apply`}</title>
      <PageHeader help={<Help slug="searches" />} title={t("searches.new")} description={t(forPack("searches.description", currentPack))} />
      <SearchForm saving={save.isPending} error={save.error}
        onSubmit={(body) => save.mutate({ body }, { onSuccess: () => { toast(t("searches.saved")); router.push("/searches"); } })} />
    </div>
  );
}
