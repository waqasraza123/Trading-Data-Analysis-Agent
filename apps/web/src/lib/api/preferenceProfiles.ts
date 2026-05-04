import { getPublicEnv } from "@/config/env";
import { apiGet, apiPatch, apiPost } from "./client";
import { listSymbols, listWorkspaces } from "./market";
import type { ApiFailure, ApiResult, UUID } from "./types";
import type {
  PreferenceProfile,
  PreferenceProfileFilterContext,
  PreferenceProfileInput,
  PreferenceProfileMatch,
  PreferenceProfilesFailure,
  PreferenceProfilesPageData,
  PreferenceProfileUpdateInput,
  StrategyProfileOption,
} from "@/lib/preferences/types";
import { preferenceProfilesFailure } from "@/lib/preferences/types";

export function listPreferenceProfiles(params: {
  workspaceId: UUID;
  userId?: UUID;
  includeArchived?: boolean;
}): Promise<ApiResult<PreferenceProfile[]>> {
  return apiGet<PreferenceProfile[]>("/preference-profiles", {
    query: {
      workspaceId: params.workspaceId,
      userId: params.userId,
      includeArchived: params.includeArchived || undefined,
      limit: 500,
    },
    optional: true,
  });
}

export function getPreferenceProfile(profileId: UUID): Promise<ApiResult<PreferenceProfile>> {
  return apiGet<PreferenceProfile>(`/preference-profiles/${profileId}`, { optional: true });
}

export function getDefaultPreferenceProfile(
  workspaceId: UUID,
): Promise<ApiResult<PreferenceProfile>> {
  return apiGet<PreferenceProfile>("/preference-profiles/default", {
    query: { workspaceId },
    optional: true,
  });
}

export function createPreferenceProfile(
  input: PreferenceProfileInput,
): Promise<ApiResult<PreferenceProfile>> {
  return apiPost<PreferenceProfile>("/preference-profiles", input, { optional: true });
}

export function updatePreferenceProfile(
  profileId: UUID,
  input: PreferenceProfileUpdateInput,
): Promise<ApiResult<PreferenceProfile>> {
  return apiPatch<PreferenceProfile>(`/preference-profiles/${profileId}`, input, {
    optional: true,
  });
}

export function archivePreferenceProfile(profileId: UUID): Promise<ApiResult<PreferenceProfile>> {
  return apiPost<PreferenceProfile>(`/preference-profiles/${profileId}/archive`, undefined, {
    optional: true,
  });
}

export function setDefaultPreferenceProfile(
  profileId: UUID,
): Promise<ApiResult<PreferenceProfile>> {
  return apiPost<PreferenceProfile>(`/preference-profiles/${profileId}/set-default`, undefined, {
    optional: true,
  });
}

export function getPreferenceProfileFilterContext(
  profileId: UUID,
): Promise<ApiResult<PreferenceProfileFilterContext>> {
  return apiGet<PreferenceProfileFilterContext>(`/preference-profiles/${profileId}/filter-context`, {
    optional: true,
  });
}

export function matchPreferenceProfileSignal(
  profileId: UUID,
  signalId: UUID,
): Promise<ApiResult<PreferenceProfileMatch>> {
  return apiPost<PreferenceProfileMatch>(
    `/preference-profiles/${profileId}/match-signal/${signalId}`,
    undefined,
    { optional: true },
  );
}

export function listStrategyProfileOptions(): Promise<ApiResult<StrategyProfileOption[]>> {
  return apiGet<StrategyProfileOption[]>("/strategy-profiles", {
    query: {
      is_active: true,
      limit: 500,
    },
    optional: true,
  });
}

export async function getPreferenceProfilesPageData(params: {
  workspaceId?: string;
  profileId?: string;
}): Promise<PreferenceProfilesPageData> {
  const env = getPublicEnv();
  const failures: PreferenceProfilesFailure[] = [];
  const [workspacesResult, symbolsResult, strategyProfilesResult] = await Promise.all([
    listWorkspaces(),
    listSymbols(),
    listStrategyProfileOptions(),
  ]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const strategyProfiles = readResult("Strategy profiles", strategyProfilesResult, [], failures);
  const workspace =
    workspaces.find((candidate) => candidate.id === params.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: params.workspaceId || null,
      selectedProfileId: params.profileId || null,
      workspace: null,
      workspaces,
      symbols,
      strategyProfiles,
      profiles: [],
      selectedProfile: null,
      filterContext: null,
      failures,
      lastUpdatedAt: new Date().toISOString(),
    };
  }

  const [profilesResult, defaultProfileResult] = await Promise.all([
    listPreferenceProfiles({ workspaceId: workspace.id }),
    getDefaultPreferenceProfile(workspace.id),
  ]);
  const profiles = readResult("Preference profiles", profilesResult, [], failures);
  const defaultProfile = readNullableResult("Default preference profile", defaultProfileResult, failures);
  const selectedProfile =
    profiles.find((profile) => profile.id === params.profileId) ||
    defaultProfile ||
    profiles.find((profile) => profile.is_default) ||
    profiles[0] ||
    null;
  const filterContextResult = selectedProfile
    ? await getPreferenceProfileFilterContext(selectedProfile.id)
    : null;
  const filterContext = filterContextResult
    ? readNullableResult("Preference filter context", filterContextResult, failures)
    : null;

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: params.workspaceId || null,
    selectedProfileId: selectedProfile?.id || params.profileId || null,
    workspace,
    workspaces,
    symbols,
    strategyProfiles,
    profiles,
    selectedProfile,
    filterContext,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: PreferenceProfilesFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readNullableResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: PreferenceProfilesFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function toFailure(label: string, result: ApiFailure): PreferenceProfilesFailure {
  return preferenceProfilesFailure(label, result);
}
