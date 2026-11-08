"use client";

import { isApiError } from "@apply/api";
import { useI18n } from "@apply/i18n/react";
import { ErrorNotice } from "@apply/kit";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { Guides } from "@/components/help";
import { Shell } from "@/components/shell";
import { useMe } from "@/lib/queries";

/** Every signed-in page. A session that has ended goes back to sign-in, then returns here. */
export default function SignedInLayout({ children }: { children: ReactNode }) {
  const me = useMe();
  const router = useRouter();
  const pathname = usePathname();
  const { t, error } = useI18n();
  const signedOut = isApiError(me.error, "UNAUTHENTICATED");

  useEffect(() => {
    if (signedOut) router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
  }, [signedOut, router, pathname]);

  if (me.isError && !signedOut) {
    return (
      <main id="main" className="p-8">
        <ErrorNotice message={error(isApiError(me.error) ? me.error.code : "NETWORK")} retryLabel={t("action.retry")}
          onRetry={() => me.refetch()} />
      </main>
    );
  }
  if (!me.data) {
    return <p role="status" className="p-8 text-sm text-muted-foreground">{t("state.loading")}</p>;
  }
  return <Guides><Shell>{children}</Shell></Guides>;
}
