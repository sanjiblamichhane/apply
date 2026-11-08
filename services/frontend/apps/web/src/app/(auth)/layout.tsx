import type { ReactNode } from "react";

import { EnglishOnly } from "./english-only";

/**
 * Signing in and the first run: glass on a soft backdrop, in English whatever this browser chose before (the
 * account's own language takes over once signed in). No language switch here; it's in Settings.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <EnglishOnly>
      <main id="main" lang="en" className="glass-backdrop grid min-h-dvh place-items-center px-4 py-12">
        {children}
      </main>
    </EnglishOnly>
  );
}
