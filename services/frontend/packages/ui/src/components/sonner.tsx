"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"

import { useUiLabels } from "../lib/ui-labels"

// shadcn/ui new-york-v4 (MIT; see NOTICE). apply's changes: exported as SonnerToaster, sonner's own icons rather
// than an icon font's, and the close button (on when a caller passes `closeButton`) named in the reader's
// language, with a visible focus ring.
const SonnerToaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()
  const { closeNotification } = useUiLabels()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      toastOptions={{
        closeButtonAriaLabel: closeNotification,
        classNames: {
          closeButton: "focus-visible:ring-2 focus-visible:ring-ring",
        },
      }}
      {...props}
    />
  )
}

export { SonnerToaster }
