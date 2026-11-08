/**
 * Job boards' application forms, read and filled over the standard DOM by the browser extension (a content
 * script), in the person's own browser while they watch. It never submits anything: the person does.
 *
 *   const adapter = adapterFor(location.href);
 *   const fields = readForm(document, adapter);
 *   const result = apply(plan(fields, sheet, adapter), { files });
 */
export { apply, fieldKey, preview, type ApplyOptions } from "./fill";
export { bare, formReady, labelFor, readForm, signature, signInShowing } from "./dom";
export { CONSENT, employerNamed, RULES, plan, sourcesFor, workedFor } from "./match";
export { ADAPTERS, adapterFor, boardHosts, type Aliases } from "./registry";
export { BOARD_LIST, hostMatches, type BoardInfo } from "./boards";
export { biggestForm, defineBoard, generic, stripForm, THANKS, type BoardSpec } from "./define";
export * from "./adapters/more";
export { board03 } from "./adapters/board03";
export { board01 } from "./adapters/board01";
export { board02 } from "./adapters/board02";
export type * from "./types";
