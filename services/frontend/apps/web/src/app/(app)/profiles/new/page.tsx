"use client";

import { useI18n } from "@apply/i18n/react";
import { PageHeader } from "@apply/kit";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { ProfileForm } from "@/components/profile-form";
import { ProfileImport } from "@/components/profile-import";
import { SchemaProfileForm } from "@/components/schema-profile-form";
import { useCurrentPack } from "@/lib/pack-choice";
import { useCreateProfile, usePack } from "@/lib/queries";
import { TAILORED_PACK } from "@/lib/schema-labels";

export default function NewProfilePage() {
  const { t } = useI18n();
  const router = useRouter();
  const create = useCreateProfile();
  const [currentPack] = useCurrentPack();
  const pack = usePack(currentPack);
  const done = {
    onSuccess: () => {
      toast(t("profiles.saved"));
      router.push("/profiles");
    },
  };
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${t("profiles.new")} · apply`}</title>
      <PageHeader help={<Help slug="profiles" />} title={t("profiles.new")} description={t("profiles.description")} />
      <ProfileImport pack={currentPack} />
      <h2 className="text-lg font-semibold">{t("profiles.import.or")}</h2>
      {currentPack === TAILORED_PACK ? (
        <ProfileForm saving={create.isPending} error={create.error}
          onSubmit={(body) => create.mutate({ pack: currentPack, kind: "individual", ...body }, done)} />
      ) : pack.data ? (
        <SchemaProfileForm key={currentPack} pack={pack.data} saving={create.isPending} error={create.error}
          onSubmit={(body) => create.mutate({ pack: currentPack, ...body }, done)} />
      ) : (
        <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p>
      )}
    </div>
  );
}
