"use client"

import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"

import { cn } from "../lib/utils"

// shadcn/ui new-york-v4 (MIT; see NOTICE). apply's changes:
// - The thumb is solid muted-foreground, 4.5:1 or more on the background, card and popover it sits on in both
//   themes (lib/contrast.ts), where the upstream border colour is about 1.3:1 (WCAG 1.4.11 asks for 3:1).
// - Content is laid out at the area's width (a block, not Radix's table), so text wraps instead of being cut off
//   at the edge (WCAG 1.4.10). Wide content still scrolls sideways when a horizontal ScrollBar is added.
// - `label` names the scrolling element and puts it in the tab order, so keyboard users can reach and scroll it
//   (WCAG 2.1.1); `viewportClassName` and `viewportRef` reach the scrolling element itself.
// - A solid focus outline, drawn inside the edge so the area's rounding never clips it.
// - The scrolling element is `relative`: what's absolutely placed inside it (a screen reader's hidden label, an
//   `sr-only` span) is clipped and scrolls with it, instead of reaching past the area and making the page scroll.

type ScrollAreaProps = React.ComponentProps<typeof ScrollAreaPrimitive.Root> & {
  /** Accessible name of the scrolling region. Given one, the region can be focused and scrolled by keyboard. */
  label?: string
  /** Classes for the element that scrolls (padding, `overscroll-contain`, a max height, edge shadows). */
  viewportClassName?: string
  /** The element that scrolls, e.g. to read or set its scroll position. */
  viewportRef?: React.Ref<HTMLDivElement>
}

function ScrollArea({
  className,
  children,
  label,
  viewportClassName,
  viewportRef,
  ...props
}: ScrollAreaProps) {
  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        data-slot="scroll-area-viewport"
        ref={viewportRef}
        {...(label ? { role: "region", "aria-label": label, tabIndex: 0 } : {})}
        className={cn(
          "relative size-full rounded-[inherit] outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring [&>div]:block!",
          viewportClassName
        )}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

function ScrollBar({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>) {
  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot="scroll-area-scrollbar"
      orientation={orientation}
      className={cn(
        "flex touch-none p-px transition-colors select-none",
        orientation === "vertical" &&
          "h-full w-2.5 border-s border-s-transparent",
        orientation === "horizontal" &&
          "h-2.5 flex-col border-t border-t-transparent",
        className
      )}
      {...props}
    >
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot="scroll-area-thumb"
        className="relative flex-1 rounded-full bg-muted-foreground"
      />
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  )
}

export { ScrollArea, ScrollBar }
export type { ScrollAreaProps }
