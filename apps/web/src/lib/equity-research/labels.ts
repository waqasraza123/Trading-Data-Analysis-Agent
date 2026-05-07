import type { SymbolRead, UUID } from "@/lib/api/types";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";

export const equityScanProfiles = [
  "continuation_momentum",
  "constructive_pullback",
  "breakout_retest",
  "reversal_watch",
  "avoid_chop_or_stale",
] as const;

export const equityTimeframes = ["1d", "4h", "1h"] as const;

export const equitySetupTypeFilters = [
  "all",
  "continuation",
  "momentum",
  "pullback",
  "breakout_retest",
  "reversal_watch",
  "range_break",
  "no_clear_setup",
] as const;

export const equityCandidateStatusFilters = [
  "all",
  "candidate",
  "needs_confirmation",
  "conflicted",
  "avoid",
  "insufficient_data",
  "stale_data",
] as const;

export const equityQualityFilters = [
  "all",
  "strong_context",
  "acceptable_context",
  "mixed_context",
  "review_required",
  "avoid_condition",
  "insufficient_context",
] as const;

export function equityStatusTone(
  value: string | null | undefined,
): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase();
  if (normalized === "candidate" || normalized === "completed" || normalized === "active") {
    return "good";
  }
  if (
    normalized === "needs_confirmation" ||
    normalized === "mixed_context" ||
    normalized === "completed_with_warnings" ||
    normalized === "paused" ||
    normalized === "review_required"
  ) {
    return "warning";
  }
  if (
    normalized === "avoid" ||
    normalized === "avoid_condition" ||
    normalized === "failed" ||
    normalized === "archived"
  ) {
    return "danger";
  }
  if (normalized === "running" || normalized === "pending") {
    return "info";
  }
  return "neutral";
}

export function equityLabel(value: string | null | undefined, fallback = "Review context"): string {
  const label = humanizeLabel(value);
  return label.trim() || fallback;
}

export function equitySymbolLabel(symbols: SymbolRead[], symbolId: UUID | null | undefined): string {
  if (!symbolId) {
    return "Unknown symbol";
  }
  const symbol = symbols.find((candidate) => candidate.id === symbolId);
  return symbol ? `${symbol.symbol} · ${symbol.display_name}` : shortIdentifier(symbolId);
}

export function compactEquitySymbol(symbols: SymbolRead[], symbolId: UUID | null | undefined): string {
  if (!symbolId) {
    return "Symbol";
  }
  return symbols.find((candidate) => candidate.id === symbolId)?.symbol || shortIdentifier(symbolId);
}

export function formatScore(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Unknown";
  }
  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) {
    return "Unknown";
  }
  return `${Math.round(numberValue * 100)}%`;
}

export function jsonValueLabel(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Unknown";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}
