import { cookies } from "next/headers";
import { getPublicEnv } from "@/config/env";
import { getServerApiProxyEnv } from "@/config/serverEnv";
import type { AccountData, AccountFailure, AuthActivityEvent, AuthContext, AuthSession } from "./account";
import type { ApiResult } from "./types";

export async function getAccountData(): Promise<AccountData> {
  const publicEnv = getPublicEnv();
  const serverEnv = getServerApiProxyEnv();
  const cookieStore = await cookies();
  const token = cookieStore.get(serverEnv.authSessionCookieName)?.value || null;
  const failures: AccountFailure[] = [];
  const [contextResult, sessionsResult, activityResult] = await Promise.all([
    serverApiGet<AuthContext>("/auth/context", token),
    serverApiGet<AuthSession[]>("/auth/sessions", token),
    serverApiGet<AuthActivityEvent[]>("/auth/activity", token),
  ]);
  const authContext = readResult("Auth context", contextResult, null, failures);
  const sessions = readResult("Session inventory", sessionsResult, [], failures);
  const activity = readResult("Account activity", activityResult, [], failures);
  return {
    appName: publicEnv.appName,
    authContext,
    sessions,
    activity,
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

async function serverApiGet<T>(path: string, token: string | null): Promise<ApiResult<T>> {
  const serverEnv = getServerApiProxyEnv();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${serverEnv.apiBaseUrl}${normalizedPath}`).toString();
  const headers: Record<string, string> = { accept: "application/json" };
  if (token) {
    headers.authorization = `Bearer ${token}`;
  }
  try {
    const response = await fetch(url, {
      method: "GET",
      headers,
      cache: "no-store",
    });
    const payload = await parseResponse(response);
    if (!response.ok) {
      return {
        ok: false,
        error: {
          status: response.status,
          code: extractErrorCode(payload, response.status),
          message: extractErrorMessage(payload, response.statusText),
          url,
          missing: response.status === 404,
        },
      };
    }
    return {
      ok: true,
      status: response.status,
      url,
      data: payload as T,
    };
  } catch {
    return {
      ok: false,
      error: {
        status: 0,
        code: "network_error",
        message: "Unable to reach API",
        url,
        missing: false,
      },
    };
  }
}

async function parseResponse(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { message: text };
  }
}

function extractErrorCode(payload: unknown, status: number): string {
  const apiError = extractApiError(payload);
  if (apiError && typeof apiError.code === "string") {
    return apiError.code;
  }
  if (isRecord(payload) && typeof payload.code === "string") {
    return payload.code;
  }
  if (isRecord(payload) && typeof payload.detail === "string") {
    return payload.detail;
  }
  return `http_${status}`;
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  const apiError = extractApiError(payload);
  if (apiError && typeof apiError.message === "string") {
    return apiError.message;
  }
  if (isRecord(payload) && typeof payload.message === "string") {
    return payload.message;
  }
  if (isRecord(payload) && typeof payload.detail === "string") {
    return payload.detail;
  }
  return fallback || "Request failed";
}

function extractApiError(payload: unknown): Record<string, unknown> | null {
  if (!isRecord(payload)) {
    return null;
  }
  const error = payload.error;
  return isRecord(error) ? error : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: AccountFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push({ ...result.error, label });
  return fallback;
}
