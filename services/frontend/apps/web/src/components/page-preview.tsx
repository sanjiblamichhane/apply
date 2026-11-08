"use client";

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@apply/ui";
import type { ReactNode } from "react";

/**
 * A document's page as it will be downloaded, in a frame that runs nothing and reaches nowhere (sandbox, srcdoc:
 * the page is apply's own, escaped, and its template checked). The frame is named for screen readers and can
 * be scrolled from the keyboard once focused.
 */
export function PagePreview({ html, title }: { html: string; title: string }) {
  return (
    <iframe title={title} srcDoc={html} sandbox=""
      className="h-[min(70dvh,60rem)] w-full rounded-md border bg-white focus-visible:outline-2 focus-visible:outline-ring" />
  );
}

/** A large dialog with a page in it, and what can be done with it (download, use) below. */
export function PreviewDialog({ open, onOpenChange, title, description, children, actions }: {
  open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[95dvh] overflow-y-auto sm:max-w-4xl" aria-describedby="preview-description">
        <DialogHeader className="pe-10">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription id="preview-description">{description}</DialogDescription>
        </DialogHeader>
        {children}
        {actions ? <DialogFooter className="gap-2">{actions}</DialogFooter> : null}
      </DialogContent>
    </Dialog>
  );
}
