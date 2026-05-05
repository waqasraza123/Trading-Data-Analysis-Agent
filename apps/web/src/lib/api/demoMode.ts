import { apiGet, apiPost } from "./client";
import type { ApiResult } from "./types";
import type { DemoModeRunFullFlow, DemoModeStatus } from "@/lib/demo-mode/types";

export function getDemoModeStatus(): Promise<ApiResult<DemoModeStatus>> {
  return apiGet<DemoModeStatus>("/demo-mode/status", { optional: true });
}

export function runDemoModeFullFlow(): Promise<ApiResult<DemoModeRunFullFlow>> {
  return apiPost<DemoModeRunFullFlow>(
    "/demo-mode/run-full-flow",
    {
      include_journal_entry: true,
      force_recompute: false,
    },
    {
      optional: true,
      timeoutMs: 180000,
    },
  );
}
