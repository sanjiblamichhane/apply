"use client";

import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import { SplitView } from "@apply/kit";
import { useSelectedLayoutSegment } from "next/navigation";
import { type ReactNode, Suspense } from "react";

import { useCurrentPack } from "@/lib/pack-choice";
import { ApplicationsIndex } from "@/components/applications-index";

/** The board or list, with an application's detail beside it on wide screens (alone on narrow ones). */
export default function ApplicationsLayout({ children }: { children: ReactNode }) {
  const selected = useSelectedLayoutSegment();
  const { t } = useI18n();
  const [currentPack] = useCurrentPack();
  return (
    <SplitView
      primary={<Suspense><ApplicationsIndex beside={Boolean(selected)} /></Suspense>}
      detail={selected ? children : null}
      detailLabel={t(forPack("opportunity.details", currentPack))}
    />
  );
}
