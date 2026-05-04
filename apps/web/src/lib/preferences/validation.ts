import type { PreferenceProfileInput } from "@/lib/preferences/types";

export type PreferenceValidationResult = {
  valid: boolean;
  errors: string[];
};

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function validatePreferenceProfileInput(
  input: PreferenceProfileInput,
): PreferenceValidationResult {
  const errors: string[] = [];
  if (!isUuid(input.workspace_id)) {
    errors.push("Workspace is required.");
  }
  if (!input.name.trim()) {
    errors.push("Profile name is required.");
  }
  if (input.name.trim().length > 160) {
    errors.push("Profile name must be 160 characters or fewer.");
  }
  if ((input.description || "").trim().length > 5000) {
    errors.push("Description must be 5000 characters or fewer.");
  }
  if (input.minimum_confidence !== undefined && !isScore(input.minimum_confidence)) {
    errors.push("Minimum confidence must be between 0 and 1.");
  }
  if (input.minimum_setup_quality !== undefined && !isScore(input.minimum_setup_quality)) {
    errors.push("Minimum setup quality must be between 0 and 1.");
  }
  if (
    input.max_stale_seconds !== undefined &&
    (!Number.isInteger(input.max_stale_seconds) || input.max_stale_seconds <= 0)
  ) {
    errors.push("Stale data tolerance must be a positive whole number of seconds.");
  }
  if (hasOverlap(input.symbol_ids_json, input.excluded_symbol_ids_json)) {
    errors.push("A symbol cannot be both preferred and avoided.");
  }
  if (hasOverlap(input.pattern_types_json, input.excluded_pattern_types_json)) {
    errors.push("A pattern cannot be both included and avoided.");
  }
  return { valid: errors.length === 0, errors };
}

export function parseOptionalScore(value: string): number | undefined {
  if (!value.trim()) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

export function parseOptionalPositiveInteger(value: string): number | undefined {
  if (!value.trim()) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : Number.NaN;
}

function isScore(value: number): boolean {
  return Number.isFinite(value) && value >= 0 && value <= 1;
}

function isUuid(value: string | null | undefined): value is string {
  return Boolean(value && uuidPattern.test(value));
}

function hasOverlap(left: string[], right: string[]): boolean {
  const rightSet = new Set(right);
  return left.some((item) => rightSet.has(item));
}
