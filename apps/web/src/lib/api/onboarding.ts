import { getPublicEnv } from "@/config/env";
import { apiGet, apiPost } from "./client";
import { listWorkspaces } from "./market";
import type { ApiFailure, ApiResult, JsonRecord, UUID } from "./types";
import type {
  OnboardingActionResponse,
  OnboardingActionType,
  OnboardingPageData,
  OnboardingStatusResponse,
} from "@/lib/onboarding/types";

export function getOnboardingStatus(params: {
  workspaceId?: UUID | null;
  userId?: UUID | null;
} = {}): Promise<ApiResult<OnboardingStatusResponse>> {
  return apiGet<OnboardingStatusResponse>("/onboarding/status", {
    query: {
      workspaceId: params.workspaceId || undefined,
      userId: params.userId || undefined,
    },
    optional: true,
    timeoutMs: 12000,
  });
}

export function runOnboardingAction(input: {
  actionType: OnboardingActionType;
  workspaceId?: UUID | null;
  userId?: UUID | null;
  options?: JsonRecord;
}): Promise<ApiResult<OnboardingActionResponse>> {
  return apiPost<OnboardingActionResponse>(
    "/onboarding/actions",
    {
      actionType: input.actionType,
      workspaceId: input.workspaceId || undefined,
      userId: input.userId || undefined,
      options: input.options || {},
    },
    {
      optional: true,
      timeoutMs: input.actionType === "run_demo_flow" ? 60000 : 30000,
    },
  );
}

export async function getOnboardingPageData(params: {
  workspaceId?: UUID;
  userId?: UUID;
}): Promise<OnboardingPageData> {
  const env = getPublicEnv();
  const [statusResult, workspacesResult] = await Promise.all([
    getOnboardingStatus(params),
    listWorkspaces(),
  ]);
  const workspaces = workspacesResult.ok ? workspacesResult.data : [];
  const status = statusResult.ok ? statusResult.data : null;
  return {
    appName: env.appName,
    status,
    statusError: statusResult.ok ? null : statusResult.error,
    workspaces,
    selectedWorkspaceId: status?.workspace.workspace_id || params.workspaceId || null,
  };
}

export function onboardingFailure(label: string, result: ApiFailure) {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
