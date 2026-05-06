import type { DailyWorkflowActionType } from "./types";
import { sanitizeUnsafeCopy } from "@/lib/safety/safeCopy";

export const dailyWorkflowActionLabels: Record<DailyWorkflowActionType, string> = {
  run_daily_workflow: "Run deterministic daily workflow",
  refresh_provider_health: "Refresh provider health",
  generate_daily_brief: "Generate brief",
  score_recent_signals: "Score recent signals",
  refresh_market_memory: "Refresh market memory",
  run_product_readiness: "Run readiness checklist",
};

export function dailyWorkflowActionLabel(actionType: DailyWorkflowActionType): string {
  return sanitizeUnsafeCopy(dailyWorkflowActionLabels[actionType]);
}
