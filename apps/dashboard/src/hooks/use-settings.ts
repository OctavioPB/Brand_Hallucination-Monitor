"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getApiKeys,
  createApiKey,
  revokeApiKey,
  getWebhooks,
  createWebhook,
  type ApiKeyCreate,
  type WebhookCreate,
} from "@/lib/api-client";

export const API_KEYS_KEY = ["api-keys"] as const;
export const WEBHOOKS_KEY = ["webhooks"] as const;

export function useApiKeys() {
  return useQuery({ queryKey: API_KEYS_KEY, queryFn: getApiKeys });
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApiKeyCreate) => createApiKey(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: API_KEYS_KEY }),
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => revokeApiKey(keyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: API_KEYS_KEY }),
  });
}

export function useWebhooks() {
  return useQuery({ queryKey: WEBHOOKS_KEY, queryFn: getWebhooks });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WebhookCreate) => createWebhook(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WEBHOOKS_KEY }),
  });
}
