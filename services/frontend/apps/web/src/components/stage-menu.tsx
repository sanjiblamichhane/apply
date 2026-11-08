"use client";

import type { Application, Stage } from "@apply/api";
import { forPack } from "@apply/i18n";
import { useI18n } from "@apply/i18n/react";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@apply/ui";
import { ArrowRight, ChevronDown } from "@apply/ui/icons";
import { toast } from "sonner";

import { boardStages } from "@/lib/board";
import { useMove } from "@/lib/queries";

/**
 * "Move to…": the keyboard (and everyone's) way to change an application's stage. Compact on a card (an icon
 * button named after the application), full on the detail page (the current stage as its label).
 */
export function StageMenu({ application, stages, compact = false }: {
  application: Application;
  stages: Stage[];
  compact?: boolean;
}) {
  const { t, pick } = useI18n();
  const move = useMove();
  const current = stages.find((s) => s.id === application.stage.id);
  const title = application.opportunity.title || t(forPack("applications.card.untitled", application.opportunity.pack));

  function choose(code: string) {
    if (code === application.stage.code) return;
    const target = stages.find((s) => s.code === code);
    move.mutate({ id: application.id, stage_code: code }, {
      onSuccess: () => toast(t("applications.moved", { stage: pick(target?.label) })),
      onError: () => toast.error(t("applications.move_failed")),
    });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {compact ? (
          <Button variant="ghost" size="icon" className="relative z-10 shrink-0"
            aria-label={t("applications.move_named", { title })}>
            <ArrowRight aria-hidden />
          </Button>
        ) : (
          <Button variant="outline" className="gap-2" aria-label={`${t("application.stage")}: ${pick(current?.label)}`}>
            <span className="text-muted-foreground">{t("application.stage")}:</span>
            <span>{pick(current?.label)}</span>
            <ChevronDown aria-hidden />
          </Button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel>{t("applications.move")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={application.stage.code} onValueChange={choose}>
          {boardStages(stages).map((stage) => (
            <DropdownMenuRadioItem key={stage.id} value={stage.code}>{pick(stage.label)}</DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
