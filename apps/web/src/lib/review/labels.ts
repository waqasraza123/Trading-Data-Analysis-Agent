import { humanizeLabel } from "@/lib/formatting/labels";

export const outcomeReviewHorizonOptions = [5, 15, 30, 60];

export const outcomeReviewLabelOptions = [
  "continuation",
  "partial_follow_through",
  "no_follow_through",
  "reversal",
  "sideways_after_signal",
  "insufficient_data",
  "not_directional",
  "failed",
];

const outcomeLabels: Record<string, string> = {
  continuation: "Observed continuation",
  partial_follow_through: "Observed partial continuation",
  no_follow_through: "No follow-through observed",
  reversal: "Observed reversal",
  sideways_after_signal: "Sideways after signal",
  insufficient_data: "Insufficient outcome data",
  not_directional: "Not directional",
  failed: "Outcome evaluation failed",
};

const reflectionLabels: Record<string, string> = {
  aligned_with_observed_outcome: "Aligned with observed outcome",
  conflicted_with_observed_outcome: "Conflicted with observed outcome",
  inconclusive: "Inconclusive",
  insufficient_outcome_data: "Insufficient outcome data",
  needs_more_review: "Needs more review",
};

const safeLabels: Record<string, string> = {
  reviewed: "Reviewed",
  observed: "Observed",
  ignored: "Ignored",
  paper_followed: "Paper followed",
  external_action_taken: "External action noted",
  no_action: "No action noted",
  uncertain: "Uncertain",
  bullish: "Bullish bias",
  bearish: "Bearish bias",
  neutral: "Neutral",
  unclear: "Unclear",
  degraded: "Degraded reliability",
  stable: "Stable reliability",
  improving: "Improving reliability",
  under_confident: "Under-confident",
  over_confident: "Over-confident",
  aligned: "Aligned",
  drift_detected: "Drift detected",
  material_drift: "Material drift",
  severe_drift: "Severe drift",
};

export function reviewLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  return outcomeLabels[value] || reflectionLabels[value] || safeLabels[value] || humanizeLabel(value);
}

export function outcomeTone(value: string | null | undefined): "neutral" | "good" | "warning" | "danger" | "info" {
  if (value === "continuation" || value === "partial_follow_through") {
    return "good";
  }
  if (value === "reversal") {
    return "danger";
  }
  if (value === "no_follow_through" || value === "sideways_after_signal") {
    return "warning";
  }
  if (value === "insufficient_data" || value === "not_directional") {
    return "info";
  }
  return "neutral";
}

export function diagnosticTone(value: string | null | undefined): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase();
  if (!normalized) {
    return "neutral";
  }
  if (normalized.includes("stable") || normalized.includes("aligned") || normalized.includes("improving")) {
    return "good";
  }
  if (normalized.includes("degraded") || normalized.includes("drift") || normalized.includes("over")) {
    return "warning";
  }
  if (normalized.includes("severe") || normalized.includes("failed")) {
    return "danger";
  }
  return "info";
}

export function describeObservedOutcome(value: string | null | undefined): string {
  if (value === "continuation" || value === "partial_follow_through") {
    return "Continuation was observed in the evaluated horizon.";
  }
  if (value === "reversal") {
    return "Reversal was observed in the evaluated horizon.";
  }
  if (value === "no_follow_through" || value === "sideways_after_signal") {
    return "No clear follow-through was observed in the evaluated horizon.";
  }
  if (value === "insufficient_data") {
    return "The backend does not have enough future candles for this horizon yet.";
  }
  return "The backend returned a non-directional or unavailable outcome state.";
}
