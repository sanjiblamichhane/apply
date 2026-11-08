"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice, PageHeader } from "@apply/kit";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogTitle, AlertDialogTrigger, Button,
} from "@apply/ui";
import { Trash } from "@apply/ui/icons";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { Help } from "@/components/help";
import { SearchForm } from "@/components/search-form";
import { useDeleteSearch, useSaveSearch, useSearches } from "@/lib/discovery";

export default function EditSearchPage() {
  const { id } = useParams<{ id: string }>();
  const { t, error } = useI18n();
  const router = useRouter();
  const searches = useSearches();
  const save = useSaveSearch();
  const remove = useDeleteSearch();
  const search = searches.data?.find((s) => s.id === id);

  if (searches.error) return <ErrorNotice message={error(isApiError(searches.error) ? searches.error.code : "INTERNAL")} />;
  if (searches.isSuccess && !search) return <ErrorNotice message={error("SEARCH_NOT_FOUND")} />;
  if (!search) return <p role="status" className="text-sm text-muted-foreground">{t("state.loading")}</p>;

  const deleteButton = (
    <AlertDialog>
      <AlertDialogTrigger asChild><Button variant="outline" className="gap-2"><Trash aria-hidden />{t("action.delete")}</Button></AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogTitle>{t("searches.delete_confirm.title")}</AlertDialogTitle>
        <AlertDialogDescription>{t("searches.delete_confirm.body")}</AlertDialogDescription>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("action.cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={() => remove.mutate(id, { onSuccess: () => { toast(t("searches.deleted")); router.push("/searches"); } })}>
            {t("action.delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${search.name} · apply`}</title>
      <PageHeader help={<Help slug="searches" />} title={search.name} description={t("searches.edit")} actions={deleteButton} />
      <SearchForm key={search.id} search={search} saving={save.isPending} error={save.error}
        onSubmit={(body) => save.mutate({ id, body }, { onSuccess: () => toast(t("searches.saved")) })} />
    </div>
  );
}
