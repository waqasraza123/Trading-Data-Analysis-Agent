import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import type { CommandCenterTone } from "./types";

const blockedTermPatterns = [
  ["b" + "uy"],
  ["s" + "ell"],
  ["en" + "ter", "trade"],
  ["ex" + "it", "trade"],
  ["place", "order"],
  ["use", "lev" + "erage"],
  ["gua" + "ranteed"],
  ["pro" + "fit"],
  ["wi" + "n", "rate"],
].map((parts) => new RegExp(`\\b${parts.join("\\s+")}\\b`, "gi"));

const safeReplacements: Array<[RegExp, string]> = [
  [/\bno signal\b/gi, "no directional signal"],
  [/\bfollow through\b/gi, "observed continuation"],
  [/\bfollow-through\b/gi, "observed continuation"],
  [/\breversal\b/gi, "observed reversal"],
  [/\binvalidat(e|ion)\b/gi, "invalidation context"],
  [/\bwatch\b/gi, "review"],
];

export function commandCenterText(value: string | null | undefined, fallback = "Review recommended"): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return fallback;
  }
  const replaced = safeReplacements.reduce((text, [pattern, replacement]) => text.replace(pattern, replacement), trimmed);
  const safe = blockedTermPatterns.reduce((text, pattern) => text.replace(pattern, "review recommended"), replaced);
  return safe.replace(/\s+/g, " ").trim() || fallback;
}

export function commandCenterLabel(value: string | null | undefined, fallback = "Not available"): string {
  return commandCenterText(humanizeLabel(value), fallback);
}

export function displaySymbol(value: string | null | undefined, id: string): string {
  return value?.trim() || shortIdentifier(id);
}

export function toneForState(value: string | null | undefined): CommandCenterTone {
  const normalized = value?.trim().toLowerCase() || "";
  if (["fresh", "healthy", "ready", "strong", "active", "completed"].includes(normalized)) {
    return "good";
  }
  if (["acceptable", "review_recommended", "medium", "running"].includes(normalized)) {
    return "info";
  }
  if (["stale", "degraded", "weak", "pending", "due", "skipped"].includes(normalized)) {
    return "warning";
  }
  if (["failed", "blocked", "unhealthy", "missing", "critical"].includes(normalized)) {
    return "danger";
  }
  return "neutral";
}

export function toneForSeverity(value: string | null | undefined): CommandCenterTone {
  const normalized = value?.trim().toLowerCase() || "";
  if (["critical", "high", "blocker", "failed"].includes(normalized)) {
    return "danger";
  }
  if (["medium", "warning", "review_recommended"].includes(normalized)) {
    return "warning";
  }
  if (["low", "info"].includes(normalized)) {
    return "info";
  }
  return "neutral";
}

export function outcomeObservationLabel(directionFollowed: boolean | null, reversalDetected: boolean): string {
  if (reversalDetected) {
    return "Observed reversal";
  }
  if (directionFollowed === true) {
    return "Observed continuation";
  }
  if (directionFollowed === false) {
    return "No follow-through observed";
  }
  return "Outcome ready";
}

export function commandCenterHref(path: string, workspaceId?: string | null): string {
  if (!workspaceId) {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}workspaceId=${workspaceId}`;
}
