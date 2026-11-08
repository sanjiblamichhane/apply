// The API's types, from the backend's OpenAPI schema (services/backend/openapi.json, the source of truth).
//
//   pnpm --filter @apply/api generate          write src/schema.ts
//   node scripts/generate.mjs --check            fail if src/schema.ts is out of date (tests/schema.test.ts runs this)
import { readFileSync, writeFileSync } from "node:fs";

import openapiTS, { astToString } from "openapi-typescript";

const source = new URL("../../../../backend/openapi.json", import.meta.url);
const target = new URL("../src/schema.ts", import.meta.url);

export async function render() {
  const ast = await openapiTS(JSON.parse(readFileSync(source, "utf-8")), { alphabetize: false, defaultNonNullable: false });
  return (
    "/* eslint-disable */\n" +
    "// Generated from services/backend/openapi.json by scripts/generate.mjs. Don't edit: regenerate.\n\n" +
    astToString(ast)
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const text = await render();
  if (process.argv.includes("--check")) {
    if (readFileSync(target, "utf-8") !== text) {
      console.error("src/schema.ts is out of date: run pnpm --filter @apply/api generate");
      process.exit(1);
    }
  } else {
    writeFileSync(target, text);
  }
}
