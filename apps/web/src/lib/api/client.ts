import { getPublicEnv } from "@/config/env";
import type { ApiResult, JsonPrimitive } from "./types";

type QueryValue = JsonPrimitive | undefined;
type RequestOptions = {
  query?: Record<string, QueryValue>;
  timeoutMs?: number;
  optional?: boolean;
};
type RequestMethod = "GET" | "POST" | "PATCH" | "DELETE";
type ApiHeaders = Record<string, string>;

const defaultTimeoutMs = 7000;

export async function apiGet<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
  return apiRequest<T>("GET", path, undefined, options);
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>("POST", path, body, options);
}

export async function apiPostForm<T>(
  path: string,
  body: FormData,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  const env = getPublicEnv();
  const url = buildRequestUrl(env.apiBaseUrl, "POST", path, options.query);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || defaultTimeoutMs);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        accept: "application/json",
        ...authHeaders(env),
      },
      body,
      cache: "no-store",
      signal: controller.signal,
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
          missing: response.status === 404 && Boolean(options.optional),
        },
      };
    }
    return {
      ok: true,
      status: response.status,
      url,
      data: normalizeApiPayload(payload) as T,
    };
  } catch (error) {
    const isAbort = error instanceof Error && error.name === "AbortError";
    return {
      ok: false,
      error: {
        status: 0,
        code: isAbort ? "request_timeout" : "network_error",
        message: isAbort ? "Request timed out" : "Unable to reach API",
        url,
        missing: false,
      },
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

export function apiPatch<T>(
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>("PATCH", path, body, options);
}

export function apiDelete<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
  return apiRequest<T>("DELETE", path, undefined, options);
}

async function apiRequest<T>(
  method: RequestMethod,
  path: string,
  body: unknown,
  options: RequestOptions,
): Promise<ApiResult<T>> {
  const env = getPublicEnv();
  const url = buildRequestUrl(env.apiBaseUrl, method, path, options.query);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || defaultTimeoutMs);
  try {
    const response = await fetch(url, {
      method,
      headers: {
        accept: "application/json",
        ...authHeaders(env),
        ...(body === undefined ? {} : { "content-type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(stripUndefined(body)),
      cache: "no-store",
      signal: controller.signal,
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
          missing: response.status === 404 && Boolean(options.optional),
        },
      };
    }
    return {
      ok: true,
      status: response.status,
      url,
      data: normalizeApiPayload(payload) as T,
    };
  } catch (error) {
    const isAbort = error instanceof Error && error.name === "AbortError";
    return {
      ok: false,
      error: {
        status: 0,
        code: isAbort ? "request_timeout" : "network_error",
        message: isAbort ? "Request timed out" : "Unable to reach API",
        url,
        missing: false,
      },
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

export function authHeaders(env = getPublicEnv()): ApiHeaders {
  const headers: ApiHeaders = {};
  if (env.authMode === "dev") {
    if (env.authDevUserId) {
      headers["x-user-id"] = env.authDevUserId;
    }
    if (env.authDevWorkspaceId) {
      headers["x-workspace-id"] = env.authDevWorkspaceId;
    }
    return headers;
  }
  const bearerToken = browserBearerToken(env.authBearerTokenStorageKey);
  if (bearerToken) {
    headers.authorization = `Bearer ${bearerToken}`;
  }
  if (env.authMode === "mixed") {
    if (env.authDevUserId) {
      headers["x-user-id"] = env.authDevUserId;
    }
    if (env.authDevWorkspaceId) {
      headers["x-workspace-id"] = env.authDevWorkspaceId;
    }
  }
  return headers;
}

function browserBearerToken(storageKey: string | null): string | null {
  if (!storageKey || typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(storageKey) || window.sessionStorage.getItem(storageKey);
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, QueryValue>): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${baseUrl}${normalizedPath}`);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

function buildRequestUrl(
  baseUrl: string,
  method: RequestMethod,
  path: string,
  query?: Record<string, QueryValue>,
): string {
  const env = getPublicEnv();
  if ((method !== "GET" || env.authMode === "session") && typeof window !== "undefined") {
    return buildUrl(window.location.origin, `/api/backend/${normalizeProxyPath(path)}`, query);
  }
  return buildUrl(baseUrl, path, query);
}

function normalizeProxyPath(path: string): string {
  return path
    .split("/")
    .filter((segment) => segment.length > 0)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
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

function stripUndefined(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => stripUndefined(item));
  }
  if (!isRecord(value)) {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value)
      .filter(([, nestedValue]) => nestedValue !== undefined)
      .map(([key, nestedValue]) => [key, stripUndefined(nestedValue)]),
  );
}

function normalizeApiPayload(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeApiPayload(item));
  }
  if (!isRecord(value)) {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value).map(([key, nestedValue]) => [
      camelToSnake(key),
      normalizeApiPayload(nestedValue),
    ]),
  );
}

function camelToSnake(value: string): string {
  return value.replace(/[A-Z]/g, (match) => `_${match.toLowerCase()}`);
}
