/** Set by scripts/build.mjs: the test build's local fake boards ({"127.0.0.1:4011": "board01"}), else {}. */
declare const __BOARD_ALIASES__: Record<string, "board01" | "board02" | "board03">;
/** Where apply's API is assumed to be until the person says otherwise. */
declare const __DEFAULT_API__: string;
/** How long until the clipboard is cleared, when the person asked for that: a minute (the test build: less). */
declare const __CLEAR_AFTER_MS__: number;
