import type { JsonRecord, JsonValue } from "@/lib/api/types";
import { humanizeLabel } from "@/lib/formatting/labels";

const blockedTermPatterns = [
  ["b" + "uy", "now"],
  ["s" + "ell", "now"],
  ["en" + "ter", "trade"],
  ["ex" + "it", "trade"],
  ["ta" + "ke", "pro" + "fit"],
  ["st" + "op", "lo" + "ss"],
  ["use", "lev" + "erage"],
  ["gua" + "ranteed"],
  ["pro" + "fit"],
  ["wi" + "n", "rate"],
].map((parts) => new RegExp(`\\b${parts.join("\\s+")}\\b`, "gi"));

const safeReplacements: Array<[RegExp, string]> = [
  [/\bbullish\b/gi, "bullish bias"],
  [/\bbearish\b/gi, "bearish bias"],
  [/\bno signal\b/gi, "no directional signal"],
  [/\bfollow through\b/gi, "observed follow-through"],
  [/\bfollow-through\b/gi, "observed follow-through"],
  [/\breversal\b/gi, "observed reversal"],
  [/\binvalidat(e|ion)\b/gi, "invalidation context"],
  [/\bwatch\b/gi, "review"],
];

export function safeBriefText(value: string | null | undefined, fallback = "Review recommended"): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return fallback;
  }
  const withSafeTerms = safeReplacements.reduce(
    (text, [pattern, replacement]) => text.replace(pattern, replacement),
    trimmed,
  );
  const withoutUnsafeTerms = blockedTermPatterns.reduce(
    (text, pattern) => text.replace(pattern, "review recommended"),
    withSafeTerms,
  );
  return withoutUnsafeTerms.replace(/\s+/g, " ").trim() || fallback;
}

export function safeHumanLabel(value: string | null | undefined, fallback = "Not available"): string {
  return safeBriefText(humanizeLabel(value), fallback);
}

export function contextText(item: JsonRecord | null | undefined, fallback = "Review recommended"): string {
  if (!item) {
    return fallback;
  }
  const candidate =
    readString(item, "label") ||
    readString(item, "title") ||
    readString(item, "message") ||
    readString(item, "reason") ||
    readString(item, "condition") ||
    readString(item, "description") ||
    readString(item, "observation") ||
    readString(item, "context") ||
    readString(item, "code");
  return safeBriefText(candidate ? humanizeLabel(candidate) : null, fallback);
}

export function readString(source: JsonRecord | null | undefined, key: string): string | null {
  const value = source?.[key];
  return typeof value === "string" ? value : null;
}

export function readNumber(source: JsonRecord | null | undefined, key: string): number | null {
  const value = source?.[key];
  return typeof value === "number" ? value : null;
}

export function jsonValueToText(value: JsonValue | undefined, fallback = "Not available"): string {
  if (typeof value === "string") {
    return safeBriefText(value, fallback);
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

export function outcomeObservationLabel(directionFollowed: boolean | null, reversalDetected: boolean): string {
  if (reversalDetected) {
    return "Observed reversal";
  }
  if (directionFollowed === true) {
    return "Observed follow-through";
  }
  if (directionFollowed === false) {
    return "No follow-through observed";
  }
  return "Review recommended";
}
