"use client";

import { call, type NewToken, type Scope, type Token } from "@apply/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

export const SCOPES = ["applications:read", "applications:write", "submissions:write", "profiles:read"] as const;
export const KINDS = ["extension", "agent"] as const;
export type TokenKind = (typeof KINDS)[number];
/** What each kind of token may carry (the API's tokens.ALLOWED): an agent never records a submission. */
export const KIND_SCOPES: Record<TokenKind, readonly Scope[]> = {
  extension: SCOPES,
  agent: ["applications:read", "applications:write", "profiles:read"],
};
export const EXPIRIES = [30, 90, 365, null] as const;

/** Whether a token still works. */
export function tokenState(token: Pick<Token, "revoked_at" | "expires_at">, now: number = Date.now()): "active" | "expired" | "revoked" {
  if (token.revoked_at) return "revoked";
  if (token.expires_at && new Date(token.expires_at).getTime() <= now) return "expired";
  return "active";
}

/** Working tokens first (newest first), then the rest. */
export function sortTokens(tokens: Token[], now: number = Date.now()): Token[] {
  const rank = (t: Token) => (tokenState(t, now) === "active" ? 0 : 1);
  return [...tokens].sort((a, b) => rank(a) - rank(b) || b.id.localeCompare(a.id));
}

export function useTokens() {
  return useQuery({ queryKey: ["tokens"], queryFn: async () => (await call(api.GET("/api/v1/tokens"))).items });
}

export function useCreateToken() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: NewToken) => call(api.POST("/api/v1/tokens", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["tokens"] }),
  });
}

export function useRevokeToken() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/tokens/{token_id}", { params: { path: { token_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["tokens"] }),
  });
}
