export type PublicEnv = {
  apiBaseUrl: string;
  appName: string;
  authMode: string;
  authDevUserId: string | null;
  authDevWorkspaceId: string | null;
  authBearerTokenStorageKey: string | null;
};

const defaultApiBaseUrl = "http://127.0.0.1:8000";
const defaultAppName = "Daily Trading Dashboard";
const defaultAuthBearerTokenStorageKey = "trading_intelligence_auth_token";

export function getPublicEnv(): PublicEnv {
  return {
    apiBaseUrl: normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
    appName: process.env.NEXT_PUBLIC_APP_NAME?.trim() || defaultAppName,
    authMode: normalizeAuthMode(process.env.NEXT_PUBLIC_AUTH_MODE),
    authDevUserId: optionalValue(process.env.NEXT_PUBLIC_AUTH_DEV_USER_ID),
    authDevWorkspaceId: optionalValue(process.env.NEXT_PUBLIC_AUTH_DEV_WORKSPACE_ID),
    authBearerTokenStorageKey: optionalValue(
      process.env.NEXT_PUBLIC_AUTH_BEARER_TOKEN_STORAGE_KEY,
    ) || defaultAuthBearerTokenStorageKey,
  };
}

function normalizeApiBaseUrl(value: string | undefined): string {
  const baseUrl = value?.trim() || defaultApiBaseUrl;
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

function normalizeAuthMode(value: string | undefined): string {
  const normalized = value?.trim().toLowerCase() || "dev";
  return ["dev", "api_key", "jwt", "session", "mixed"].includes(normalized) ? normalized : "dev";
}

function optionalValue(value: string | undefined): string | null {
  const normalized = value?.trim();
  return normalized || null;
}
