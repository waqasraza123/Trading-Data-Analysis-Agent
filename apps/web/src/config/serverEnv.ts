const defaultApiBaseUrl = "http://127.0.0.1:8000";
const defaultApiKeyHeaderName = "x-api-key";
export const defaultAuthSessionCookieName = "trading_intelligence_session";

export type ServerApiProxyEnv = {
  apiBaseUrl: string;
  apiKeyHeaderName: string;
  adminApiKey: string | null;
  authSessionCookieName: string;
};

export function getServerApiProxyEnv(): ServerApiProxyEnv {
  return {
    apiBaseUrl: normalizeApiBaseUrl(
      process.env.WEB_API_PROXY_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL,
    ),
    apiKeyHeaderName: optionalValue(
      process.env.WEB_API_PROXY_API_KEY_HEADER || process.env.API_KEY_HEADER_NAME,
    ) || defaultApiKeyHeaderName,
    adminApiKey: optionalValue(
      process.env.WEB_API_PROXY_ADMIN_API_KEY || process.env.ADMIN_API_KEY,
    ),
    authSessionCookieName:
      optionalValue(process.env.WEB_AUTH_SESSION_COOKIE) || defaultAuthSessionCookieName,
  };
}

function normalizeApiBaseUrl(value: string | undefined): string {
  const baseUrl = value?.trim() || defaultApiBaseUrl;
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

function optionalValue(value: string | undefined): string | null {
  const normalized = value?.trim();
  return normalized || null;
}
