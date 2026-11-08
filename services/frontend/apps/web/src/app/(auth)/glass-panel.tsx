import { cn, Logo } from "@apply/ui";
import type { ReactNode } from "react";

/** The sign-in pages' panel: glass (theme.css), a heading, what it's for, then the form. */
export function GlassPanel({ eyebrow, title, intro, children, className }: {
  eyebrow: string; title: string; intro: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section aria-labelledby="auth-title" className={cn("glass w-full max-w-sm rounded-3xl p-6 sm:p-8", className)}>
      <header className="mb-6 space-y-1.5">
        <Logo title={eyebrow} className="mb-3" />
        <h1 id="auth-title" className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-muted-foreground">{intro}</p>
      </header>
      {children}
    </section>
  );
}

/** Fields on glass take a stronger border: `input` would be 2.75:1 there, `muted-foreground` is at least 4.9:1. */
export const ON_GLASS_FIELD = "border-muted-foreground bg-background/90";
