import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { errors, errorText } from "../src";

const openapi = JSON.parse(
  readFileSync(new URL("../../../../backend/openapi.json", import.meta.url), "utf-8"),
) as { components: { schemas: { ErrorCode: { enum: string[] } } } };

describe("API error codes", () => {
  it("every code the API can send has a message in both languages", () => {
    const missing = openapi.components.schemas.ErrorCode.enum.filter((code) => !(code in errors));
    expect(missing, "Add these to packages/i18n/src/messages/errors.ts").toEqual([]);
  });

  it("an unknown code still says something useful", () => {
    expect(errorText("SOMETHING_NEW", "ne")).toBe(errors.INTERNAL.ne);
    expect(errorText(undefined, "en")).toBe(errors.INTERNAL.en);
  });
});
