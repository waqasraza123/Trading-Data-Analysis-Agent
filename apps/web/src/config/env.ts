export type PublicEnv = {
  apiBaseUrl: string;
  appName: string;
};

const defaultApiBaseUrl = "http://127.0.0.1:8000";
const defaultAppName = "Daily Trading Dashboard";

export function getPublicEnv(): PublicEnv {
  return {
    apiBaseUrl: normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
    appName: process.env.NEXT_PUBLIC_APP_NAME?.trim() || defaultAppName,
  };
}

function normalizeApiBaseUrl(value: string | undefined): string {
  const baseUrl = value?.trim() || defaultApiBaseUrl;
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}
