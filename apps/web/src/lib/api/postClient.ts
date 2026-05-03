import { getPublicEnv } from "@/config/env";
import type { ApiResult, JsonPrimitive } from "./types";

type QueryValue = JsonPrimitive | undefined;
type PostOptions = {
  query?: Record<string, QueryValue>;
  timeoutMs?: number;
  optional?: boolean;
};

const defaultTimeoutMs = 7000;

export async function apiPostJson<T>(
  path: string,
  body?: unknown,
  options: PostOptions = {},
): Promise<ApiResult<T>> {
  const env = getPublicEnv();
  const url = buildUrl(env.apiBaseUrl, path, options.query);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || defaultTimeoutMs);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify(stripUndefined(body || {})),
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
  if (isRecord(payload) && typeof payload.code === "string") {
    return payload.code;
  }
  if (isRecord(payload) && typeof payload.detail === "string") {
    return payload.detail;
  }
  return `http_${status}`;
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (isRecord(payload) && typeof payload.message === "string") {
    return payload.message;
  }
  if (isRecord(payload) && typeof payload.detail === "string") {
    return payload.detail;
  }
  return fallback || "Request failed";
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
