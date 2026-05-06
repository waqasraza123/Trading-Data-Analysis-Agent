import { safeCopy } from "@/lib/ui/safeCopy";
import type { OnboardingReadinessLabel, OnboardingStepState } from "./types";

export function onboardingReadinessLabel(label: OnboardingReadinessLabel): string {
  const labels: Record<OnboardingReadinessLabel, string> = {
    ready: "Ready for deterministic analysis",
    needs_setup: "Setup incomplete",
    degraded: "Readiness degraded",
    blocked: "Readiness blocked",
    unknown: "Readiness unknown",
  };
  return labels[label];
}

export function onboardingStepStateLabel(state: OnboardingStepState): string {
  const labels: Record<OnboardingStepState, string> = {
    complete: "Complete",
    incomplete: "Incomplete",
    warning: "Review",
    blocked: "Blocked",
    unavailable: "Unavailable",
  };
  return labels[state];
}

export function onboardingTone(state: OnboardingStepState | OnboardingReadinessLabel): string {
  if (state === "complete" || state === "ready") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (state === "warning" || state === "degraded") return "border-amber-200 bg-amber-50 text-amber-900";
  if (state === "blocked") return "border-rose-200 bg-rose-50 text-rose-900";
  if (state === "unavailable" || state === "unknown") return "border-slate-200 bg-slate-50 text-slate-700";
  return "border-sky-200 bg-sky-50 text-sky-900";
}

export function safeOnboardingCopy(value: string | null | undefined, fallback = "Review setup context"): string {
  return safeCopy(value, fallback);
}
