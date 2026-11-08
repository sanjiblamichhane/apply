/** boards.json, typed: every board apply knows by its address. */
import data from "./boards.json";

export type Board = keyof typeof data.boards;

export interface BoardInfo {
  key: Board;
  /** Exact hosts, or "*.suffix" for any subdomain. */
  hosts: string[];
}

export const BOARD_LIST: BoardInfo[] = Object.entries(data.boards).map(([key, b]) => ({ key: key as Board, ...b }));

/** A host pattern ("jobs.lever.co", "*.myworkdayjobs.com") matches a page's host. */
export function hostMatches(pattern: string, host: string): boolean {
  if (pattern.startsWith("*.")) {
    const suffix = pattern.slice(1); // ".myworkdayjobs.com"
    return host.endsWith(suffix) && host.length > suffix.length;
  }
  return host === pattern;
}

/** A board's hosts, for its adapter. */
export function known(board: Board): Pick<BoardInfo, "hosts"> {
  const found = BOARD_LIST.find((b) => b.key === board);
  if (!found) throw new Error(`${board} isn't in boards.json`);
  return { hosts: found.hosts };
}
