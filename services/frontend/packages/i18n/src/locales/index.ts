import type { Locale } from "../types";

type Loader = () => Promise<{ default: Record<string, string> }>;

/**
 * Each catalogue as its own chunk, loaded only for its reader. Written out (not a template path) so every bundler
 * (Next, esbuild for the extension, Vite for tests) sees each file.
 */
export const CATALOGUE_LOADERS: Record<Exclude<Locale, "en" | "ne">, Loader> = {
  es: () => import("./es.json"),
};
