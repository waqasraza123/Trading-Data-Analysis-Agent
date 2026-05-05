import type { CommandCenterTone } from "@/lib/command-center/types";
import type { DailyRoutineRunStatus, DailyRoutineStepStatus } from "./types";

export function routineStatusTone(status: DailyRoutineRunStatus | DailyRoutineStepStatus): CommandCenterTone {
  if (status === "completed") {
    return "good";
  }
  if (status === "completed_with_warnings" || status === "skipped") {
    return "warning";
  }
  if (status === "failed" || status === "cancelled") {
    return "danger";
  }
  if (status === "running" || status === "pending") {
    return "info";
  }
  return "neutral";
}

export function routineLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export function safeRoutineText(value: string | null | undefined, fallback = "Routine status recorded"): string {
  const normalized = value?.trim();
  if (!normalized) {
    return fallback;
  }
  return normalized
    .replace(/\bbuy\b/gi, "review")
    .replace(/\bsell\b/gi, "review")
    .replace(/\btrade\b/gi, "review")
    .replace(/\border\b/gi, "record");
}
