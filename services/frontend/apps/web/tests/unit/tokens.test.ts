import type { Token } from "@apply/api";
import { describe, expect, it } from "vitest";

import { sortTokens, tokenState } from "@/lib/tokens";

const now = Date.parse("2026-10-26T12:00:00Z");
const token = (id: string, extra: Partial<Token> = {}): Token => ({
  id, name: id, kind: "extension", prefix: "apl_x", scopes: ["applications:read"], created_at: "2026-10-01T00:00:00Z",
  expires_at: null, last_used_at: null, revoked_at: null, ...extra,
});

describe("tokens", () => {
  it("know whether they still work", () => {
    expect(tokenState(token("a"), now)).toBe("active");
    expect(tokenState(token("a", { expires_at: "2026-10-27T00:00:00Z" }), now)).toBe("active");
    expect(tokenState(token("a", { expires_at: "2026-10-26T11:59:59Z" }), now)).toBe("expired");
    expect(tokenState(token("a", { revoked_at: "2026-10-20T00:00:00Z" }), now)).toBe("revoked");
  });

  it("list the working ones first, newest first", () => {
    const sorted = sortTokens([token("01A", { revoked_at: "2026-10-20T00:00:00Z" }), token("01B"), token("01C")], now);
    expect(sorted.map((t) => t.id)).toEqual(["01C", "01B", "01A"]);
  });
});
