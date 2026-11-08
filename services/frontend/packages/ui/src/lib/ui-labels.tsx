"use client"

import * as React from "react"

/**
 * Words the UI components say on their own (a close button's name). This package can't
 * depend on @apply/i18n, so the app passes the translated strings in through this
 * context; English is used without it.
 */
export interface UiLabels {
  close: string
  closeNotification: string
}

export const DEFAULT_UI_LABELS: UiLabels = {
  close: "Close",
  closeNotification: "Close notification",
}

const UiLabelsContext = React.createContext<UiLabels>(DEFAULT_UI_LABELS)

export function UiLabelsProvider({
  labels,
  children,
}: {
  labels: Partial<UiLabels>
  children: React.ReactNode
}) {
  // Keyed on the labels' content, so a new object with the same words doesn't re-render every consumer.
  const key = JSON.stringify(labels)
  const value = React.useMemo(() => ({ ...DEFAULT_UI_LABELS, ...(JSON.parse(key) as Partial<UiLabels>) }), [key])
  return <UiLabelsContext.Provider value={value}>{children}</UiLabelsContext.Provider>
}

export function useUiLabels(): UiLabels {
  return React.useContext(UiLabelsContext)
}
