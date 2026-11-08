"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice, PageHeader } from "@apply/kit";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@apply/ui";
import { Copy, Save, Trash } from "@apply/ui/icons";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { IconAction } from "@/components/icon-action";
import { ProfileForm } from "@/components/profile-form";
import { ProfileReading } from "@/components/profile-import";
import { SchemaProfileForm } from "@/components/schema-profile-form";
import { useDeleteProfile, useDuplicateProfile, usePack, useProfile, useUpdateProfile } from "@/lib/queries";
import { TAILORED_PACK } from "@/lib/schema-labels";

const FORM = "profile-edit";

/**
 * A profile, to change. The header (name, Save, Duplicate, Delete) stays at the top while the long form scrolls
 * under it, so Save is always one click away. Its actions show only icons, each named for screen readers and in a
 * tooltip on hover or focus.
 */
export default function EditProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { t, error } = useI18n();
  const router = useRouter();
  const profile = useProfile(id);
  const update = useUpdateProfile(id);
  const remove = useDeleteProfile();
  const duplicate = useDuplicateProfile();
  const pack = usePack(profile.data?.pack);

  if (profile.error) {
    return <ErrorNotice message={error(isApiError(profile.error) ? profile.error.code : "INTERNAL")} />;
  }
  if (!profile.data) return <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p>;

  const copy = profile.data;
  const editing = profile.data.reading?.status !== "pending" && (profile.data.pack === TAILORED_PACK || Boolean(pack.data));
  const saveButton = editing ? (
    <IconAction type="submit" form={FORM} variant="default" disabled={update.isPending}
      label={update.isPending ? t("action.saving") : t("action.save")} icon={<Save aria-hidden />} />
  ) : null;
  const duplicateButton = (
    <IconAction label={t("profiles.duplicate")} icon={<Copy aria-hidden />} disabled={duplicate.isPending}
      onClick={() => duplicate.mutate({ id, name: t("profiles.copy_name", { name: copy.name }).slice(0, 200) }, {
        onSuccess: (made) => {
          toast(t("profiles.duplicated"));
          router.push(`/profiles/${made.id}`);
        },
      })} />
  );
  const deleteButton = (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <IconAction label={t("action.delete")} icon={<Trash aria-hidden />} />
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogTitle>{t("profiles.delete_confirm.title")}</AlertDialogTitle>
        <AlertDialogDescription>{t("profiles.delete_confirm.body")}</AlertDialogDescription>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("action.cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={() => remove.mutate(id, {
            onSuccess: () => {
              toast(t("profiles.deleted"));
              router.push("/profiles");
            },
          })}>{t("action.delete")}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${profile.data.name} · apply`}</title>
      <PageHeader help={<Help slug="profiles" />} title={profile.data.name} description={t("profiles.edit")}
        actions={<>{saveButton}{duplicateButton}{deleteButton}</>}
        className="sticky top-0 z-20 -mx-2 flex-nowrap items-center border-b bg-background px-2 py-3" />
      <ProfileReading profile={profile.data} />
      {/* While the model reads the document, no form: what's read would replace what's typed. */}
      {profile.data.reading?.status === "pending" ? null : profile.data.pack === TAILORED_PACK ? (
        <ProfileForm key={profile.data.updated_at} formId={FORM} profile={profile.data} saving={update.isPending} error={update.error}
          onSubmit={(body) => update.mutate(body, { onSuccess: () => toast(t("profiles.saved")) })} />
      ) : pack.data ? (
        <SchemaProfileForm key={profile.data.updated_at} formId={FORM} pack={pack.data} profile={profile.data} saving={update.isPending} error={update.error}
          onSubmit={({ kind: _kind, ...body }) => update.mutate(body, { onSuccess: () => toast(t("profiles.saved")) })} />
      ) : null}
    </div>
  );
}
