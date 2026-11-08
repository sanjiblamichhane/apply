import { describe, expect, it } from "vitest";

import { ApiError, call, createApi, isApiError } from "../src";

function fakeFetch(status: number, body: unknown, contentType = "application/problem+json"): typeof fetch {
  return async () =>
    new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "content-type": contentType } });
}

const PROBLEM = {
  type: "urn:apply:error:invalid-argument", status: 422, title: "Invalid argument", detail: "x",
  code: "INVALID_ATTRIBUTES", errors: [{ loc: ["body", "attributes", "skills"], msg: "Input should be a valid list", type: "list_type" }],
};

describe("call()", () => {
  it("returns the body of a successful call", async () => {
    const api = createApi("http://test", fakeFetch(200, { status: "ok", database: true, version: "0.1.0" }, "application/json"));
    await expect(call(api.GET("/api/v1/health"))).resolves.toEqual({ status: "ok", database: true, version: "0.1.0" });
  });

  it("turns a Problem into an ApiError with its code and field errors", async () => {
    const api = createApi("http://test", fakeFetch(422, PROBLEM));
    const error = await call(api.POST("/api/v1/profiles", { body: { name: "x" } })).catch((e) => e);
    expect(isApiError(error, "INVALID_ATTRIBUTES")).toBe(true);
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).fieldErrors).toEqual({ "attributes.skills": "Input should be a valid list" });
  });

  it("a server that doesn't answer is NETWORK", async () => {
    const api = createApi("http://test", async () => {
      throw new TypeError("fetch failed");
    });
    const error = await call(api.GET("/api/v1/health")).catch((e) => e);
    expect(isApiError(error, "NETWORK")).toBe(true);
  });

  it("a proxy's own 502 is NETWORK too", async () => {
    const api = createApi("http://test", fakeFetch(502, "Bad gateway", "text/plain"));
    const error = await call(api.GET("/api/v1/health")).catch((e) => e);
    expect(isApiError(error, "NETWORK")).toBe(true);
  });

  it("a 204 is fine", async () => {
    const api = createApi("http://test", fakeFetch(204, undefined));
    await expect(call(api.POST("/api/v1/auth/sign-out"))).resolves.toBeUndefined();
  });
});
