"use client";

import { call } from "@apply/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

/** The accounts on this apply and its registration switch: the owner's to see and change. */
export function usePeople(enabled: boolean) {
  return useQuery({ queryKey: ["people"], enabled, queryFn: () => call(api.GET("/api/v1/people")).then((r) => r.items) });
}

export function useRegistration(enabled: boolean) {
  return useQuery({ queryKey: ["registration"], enabled, queryFn: () => call(api.GET("/api/v1/system/registration")) });
}

export function useSetRegistration() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (open: boolean) => call(api.PUT("/api/v1/system/registration", { body: { open } })),
    onSuccess: (saved) => {
      client.setQueryData(["registration"], saved);
      void client.invalidateQueries({ queryKey: ["setup"] });
    },
  });
}

export function useTurnPerson() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, on }: { id: string; on: boolean }) => on
      ? call(api.POST("/api/v1/people/{person_id}/enable", { params: { path: { person_id: id } } }))
      : call(api.POST("/api/v1/people/{person_id}/disable", { params: { path: { person_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["people"] }),
  });
}

export function useDeletePerson() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/people/{person_id}", { params: { path: { person_id: id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["people"] }),
  });
}
