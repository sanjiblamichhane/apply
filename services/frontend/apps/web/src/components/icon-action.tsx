"use client";

import { Button, type ButtonProps, Tooltip, TooltipContent, TooltipTrigger } from "@apply/ui";
import { forwardRef, type ReactNode } from "react";

/**
 * A button that shows only its icon, with its name as the accessible name and as a tooltip on hover or keyboard
 * focus (so the name is never only in the tooltip). Forwards its ref and props, so a dialog's trigger can wrap it.
 */
export const IconAction = forwardRef<HTMLButtonElement, ButtonProps & { label: string; icon: ReactNode }>(
  ({ label, icon, variant = "outline", ...props }, ref) => (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button ref={ref} variant={variant} size="icon" aria-label={label} {...props}>
          {icon}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  ),
);
IconAction.displayName = "IconAction";
