import { board03 } from "./adapters/board03";
import { board01 } from "./adapters/board01";
import { board02 } from "./adapters/board02";
import { MORE } from "./adapters/more";
import { BOARD_LIST, hostMatches } from "./boards";
import type { Adapter, Board } from "./types";

/** Every board's adapter: the three with their own (and recorded forms, for Auto), then the declared ones. */
export const ADAPTERS: readonly Adapter[] = [board01, board02, board03, ...MORE];

/** Extra hosts standing in for a board: only the test build's local fake boards. */
export type Aliases = Partial<Record<string, Board>>;

/** The adapter for a page's address, or null if it isn't a board apply knows. */
export function adapterFor(url: URL | string, aliases: Aliases = {}): Adapter | null {
  const u = typeof url === "string" ? new URL(url) : url;
  if (u.protocol !== "https:" && !aliases[u.host]) return null;
  const board = aliases[u.host];
  if (board) return ADAPTERS.find((a) => a.board === board) ?? null;
  return ADAPTERS.find((a) => a.hosts.some((h) => hostMatches(h, u.hostname))) ?? null;
}

/** Every host pattern the boards cover (the extension's manifest is made from boards.json too). */
export function boardHosts(): string[] {
  return BOARD_LIST.flatMap((b) => b.hosts);
}
