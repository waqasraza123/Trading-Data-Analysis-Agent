import type { TriageColumnKey, TriageReason } from "./types";

export const triageColumns: Array<{
  key: TriageColumnKey;
  title: string;
  description: string;
}> = [
  {
    key: "high_quality_context",
    title: "Review First",
    description: "High-priority setups with fresh context and stronger evidence alignment.",
  },
  {
    key: "needs_confirmation",
    title: "Needs Confirmation",
    description: "Setups waiting for final-candle, outcome, or context confirmation.",
  },
  {
    key: "conflicted",
    title: "Conflicted",
    description: "Signals with mixed evidence, disagreement, or grounding concerns.",
  },
  {
    key: "avoid_no_directional_signal",
    title: "Avoid / No Directional",
    description: "Neutral, unclear, range, or avoid-condition context.",
  },
  {
    key: "stale_data_issue",
    title: "Stale / Data Issue",
    description: "Signals affected by stale memory, degraded quality, or missing data.",
  },
  {
    key: "review_required",
    title: "Review Required",
    description: "Blocked readiness, open operator review, or critical quality findings.",
  },
];

const unsafePatterns: Array<[RegExp, string]> = [
  [termPattern(["b" + "uy"]), "directional review"],
  [termPattern(["s" + "ell"]), "directional review"],
  [termPattern(["en" + "ter"]), "review"],
  [termPattern(["ex" + "it"]), "review"],
  [termPattern(["ta" + "ke", "pro" + "fit"]), "target context"],
  [termPattern(["st" + "op", "lo" + "ss"]), "invalidation context"],
  [termPattern(["wi" + "n", "rate"]), "historical observation"],
  [termPattern(["pro" + "fit"]), "observed movement"],
  [termPattern(["gua" + "ranteed"]), "uncertain"],
];

const reasonToneByLabel: Record<string, TriageReason["tone"]> = {
  "Review first": "good",
  "Needs confirmation": "warning",
  Conflicted: "warning",
  "Avoid condition": "info",
  "No directional signal": "info",
  "Stale data": "warning",
  "Review required": "danger",
  "Fresh data": "good",
  "Missing context": "neutral",
  "Grounding issue": "warning",
  "Quality finding": "warning",
  "Critical quality finding": "danger",
};

export function triageColumnTitle(key: TriageColumnKey): string {
  return triageColumns.find((column) => column.key === key)?.title || "Review Required";
}

export function reason(label: string): TriageReason {
  return {
    label: safeTriageText(label, "Review required"),
    tone: reasonToneByLabel[label] || "neutral",
  };
}

export function safeTriageText(value: string | null | undefined, fallback = "Review required"): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return fallback;
  }
  return unsafePatterns
    .reduce((text, [pattern, replacement]) => text.replace(pattern, replacement), trimmed)
    .replace(/\s+/g, " ")
    .trim();
}

export function shortReason(value: string | null | undefined, fallback = "Review required"): string {
  const safeValue = safeTriageText(value, fallback);
  return safeValue.length > 150 ? `${safeValue.slice(0, 147)}...` : safeValue;
}

function termPattern(words: string[]): RegExp {
  return new RegExp(`\\b${words.join("\\s+")}\\b`, "gi");
}
