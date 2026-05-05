import { humanizeLabel } from "@/lib/formatting/labels";
import { safeCopy } from "./safeCopy";

const safeLabelOverrides: Record<string, string> = {
  no_signal: "No directional signal",
  no_directional_signal: "No directional signal",
  bullish: "Bullish bias",
  bearish: "Bearish bias",
  review_recommended: "Review recommended",
  fresh: "Data fresh",
  stale: "Data stale",
  partial_follow_through: "Observed follow-through",
  continuation: "Observed follow-through",
  reversal: "Observed reversal",
  no_follow_through: "No follow-through observed",
  invalidation: "Invalidation context",
  target: "Target context zone",
};

export function safeLabel(value: string | null | undefined, fallback = "Not available"): string {
  if (!value) {
    return fallback;
  }
  const normalized = value.trim().toLowerCase().replace(/[\s-]+/g, "_");
  return safeCopy(safeLabelOverrides[normalized] || humanizeLabel(value), fallback);
}

export function safeSentence(value: string | null | undefined, fallback = "Not available"): string {
  return safeCopy(value, fallback);
}
