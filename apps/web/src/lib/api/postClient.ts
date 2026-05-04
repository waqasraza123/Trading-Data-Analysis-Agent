import { apiPost } from "./client";
import type { ApiResult, JsonPrimitive } from "./types";

type QueryValue = JsonPrimitive | undefined;
type PostOptions = {
  query?: Record<string, QueryValue>;
  timeoutMs?: number;
  optional?: boolean;
};

export function apiPostJson<T>(
  path: string,
  body?: unknown,
  options: PostOptions = {},
): Promise<ApiResult<T>> {
  return apiPost<T>(path, body ?? {}, options);
}
