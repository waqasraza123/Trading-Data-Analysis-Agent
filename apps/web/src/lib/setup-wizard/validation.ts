import type { UUID } from "@/lib/api/types";

export const setupStepOrder = [
  "workspace",
  "user",
  "symbols",
  "data_source",
  "credential_reference",
  "watchlist",
  "scanner_preset",
  "preference_profile",
  "demo_data",
  "readiness_check",
  "first_scan",
] as const;

export const setupTimeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"] as const;

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuid(value: string | null | undefined): value is UUID {
  return Boolean(value && uuidPattern.test(value));
}

export function requiredText(value: string, label: string): string | null {
  return value.trim() ? null : `${label} is required.`;
}

export function validateEmail(value: string): string | null {
  const normalized = value.trim().toLowerCase();
  if (!normalized || !normalized.includes("@")) {
    return "Operator email is required.";
  }
  return null;
}

export function normalizeSymbolCodes(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean),
    ),
  );
}
