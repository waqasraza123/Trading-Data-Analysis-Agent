import { apiGet, apiPost } from "./client";
import type { ApiResult, UUID } from "./types";
import type {
  ProviderConfigurationTestCreate,
  ProviderConnectionTest,
  ProviderCredentialRef,
} from "@/lib/data-onboarding/types";

export function listProviderCredentialRefs(
  workspaceId: UUID,
): Promise<ApiResult<ProviderCredentialRef[]>> {
  return apiGet<ProviderCredentialRef[]>("/provider-credentials", {
    query: {
      workspace_id: workspaceId,
      limit: 500,
    },
    optional: true,
  });
}

export function testProviderCredentialRef(
  credentialRefId: UUID,
): Promise<ApiResult<ProviderConnectionTest>> {
  return apiPost<ProviderConnectionTest>(`/provider-credentials/${credentialRefId}/test`, {}, {
    optional: true,
    timeoutMs: 12000,
  });
}

export function testProviderConfiguration(
  payload: ProviderConfigurationTestCreate,
): Promise<ApiResult<ProviderConnectionTest>> {
  return apiPost<ProviderConnectionTest>("/provider-credentials/test-provider", payload, {
    optional: true,
    timeoutMs: 12000,
  });
}
