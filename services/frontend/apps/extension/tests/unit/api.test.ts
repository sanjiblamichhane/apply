import { ApiError } from "@apply/api";
import { describe, expect, it } from "vitest";

import { ExtensionApi } from "../../src/api";

type Seen = { url: string; auth: string | null; credentials?: RequestCredentials; cookie: string | null };

function fake(answers: (url: string) => Response) {
  const seen: Seen[] = [];
  const impl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init);
    seen.push({ url: request.url, auth: request.headers.get("authorization"), credentials: init?.credentials ?? request.credentials, cookie: request.headers.get("cookie") });
    return answers(request.url);
  }) as typeof fetch;
  return { impl, seen };
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

describe("the extension's API client", () => {
  it("sends the token, and never a cookie", async () => {
    const { impl, seen } = fake(() => json({ email: "sam@example.com", locale: "ne", token: null, web_url: null }));
    const caller = await new ExtensionApi("http://127.0.0.1:8110", "apl_secret", impl).whoami();
    expect(caller.locale).toBe("ne");
    expect(seen[0]).toMatchObject({ url: "http://127.0.0.1:8110/api/v1/tokens/current", auth: "Bearer apl_secret", cookie: null });
    expect(seen[0]!.credentials).toBe("omit");
  });

  it("asks for every URL a posting may be known by, and says null when it isn't tracked", async () => {
    const { impl, seen } = fake(() => json({ code: "OPPORTUNITY_NOT_FOUND", status: 404, title: "x", type: "x", detail: "x" }, 404));
    const found = await new ExtensionApi("http://127.0.0.1:8110", "apl_x", impl).lookup(["https://a.example/1", "https://a.example/1/apply"]);
    expect(found).toBeNull();
    expect(new URL(seen[0]!.url).searchParams.getAll("url")).toEqual(["https://a.example/1", "https://a.example/1/apply"]);
  });

  it("turns API problems into codes the panel translates", async () => {
    const { impl } = fake(() => json({ code: "TOKEN_INVALID", status: 401, title: "x", type: "x", detail: "x" }, 401));
    const error = await new ExtensionApi("http://127.0.0.1:8110", "apl_x", impl).whoami().catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("TOKEN_INVALID");
  });

  it("waits while a PDF is being made", async () => {
    let calls = 0;
    const { impl } = fake(() => (++calls < 3
      ? json({ code: "RENDER_PENDING", status: 409, title: "x", type: "x", detail: "x" }, 409)
      : new Response(new Uint8Array([37, 80, 68, 70]), { status: 200 })));
    const bytes = await new ExtensionApi("http://127.0.0.1:8110", "apl_x", impl).pdf("/api/v1/x/pdf", { wait: 1 });
    expect(new TextDecoder().decode(bytes)).toBe("%PDF");
    expect(calls).toBe(3);
  });
});
