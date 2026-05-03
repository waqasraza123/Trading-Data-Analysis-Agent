import type {
  ScheduledScanConfigCreateInput,
  WatchlistCreateInput,
  WatchlistItemCreateInput,
} from "@/lib/scanner/types";

export type ValidationResult = {
  valid: boolean;
  errors: string[];
};

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function validateWatchlistCreate(input: WatchlistCreateInput): ValidationResult {
  const errors: string[] = [];
  if (!isUuid(input.workspace_id)) {
    errors.push("Workspace is required.");
  }
  if (!input.name.trim()) {
    errors.push("Watchlist name is required.");
  }
  if (input.name.trim().length > 160) {
    errors.push("Watchlist name must be 160 characters or fewer.");
  }
  if ((input.description || "").trim().length > 1000) {
    errors.push("Description must be 1000 characters or fewer.");
  }
  return { valid: errors.length === 0, errors };
}

export function validateWatchlistItemCreate(input: WatchlistItemCreateInput): ValidationResult {
  const errors: string[] = [];
  if (!isUuid(input.symbol_id)) {
    errors.push("Symbol is required.");
  }
  if (input.source_id && !isUuid(input.source_id)) {
    errors.push("Data source is invalid.");
  }
  if (!input.timeframe.trim()) {
    errors.push("Timeframe is required.");
  }
  return { valid: errors.length === 0, errors };
}

export function validateScanConfigCreate(input: ScheduledScanConfigCreateInput): ValidationResult {
  const errors: string[] = [];
  if (!isUuid(input.workspace_id)) {
    errors.push("Workspace is required.");
  }
  if (!input.name.trim()) {
    errors.push("Scan config name is required.");
  }
  if (input.name.trim().length > 160) {
    errors.push("Scan config name must be 160 characters or fewer.");
  }
  if ((input.description || "").trim().length > 1000) {
    errors.push("Description must be 1000 characters or fewer.");
  }
  if (input.scan_mode === "watchlist" && !isUuid(input.watchlist_id)) {
    errors.push("Watchlist is required for watchlist scan mode.");
  }
  if (input.scan_mode === "single_symbol") {
    if (!isUuid(input.symbol_id)) {
      errors.push("Symbol is required for single-symbol scan mode.");
    }
    if (!input.timeframe?.trim()) {
      errors.push("Timeframe is required for single-symbol scan mode.");
    }
  }
  if (input.source_id && !isUuid(input.source_id)) {
    errors.push("Data source is invalid.");
  }
  if (!Number.isInteger(input.lookback_minutes) || input.lookback_minutes < 1) {
    errors.push("Lookback minutes must be at least 1.");
  }
  if (!Number.isInteger(input.interval_seconds) || input.interval_seconds < 1) {
    errors.push("Interval seconds must be at least 1.");
  }
  return { valid: errors.length === 0, errors };
}

export function isUuid(value: string | null | undefined): value is string {
  return Boolean(value && uuidPattern.test(value));
}
