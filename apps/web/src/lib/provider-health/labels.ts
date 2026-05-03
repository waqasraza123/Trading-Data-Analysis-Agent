import type { ProviderHealthSnapshot, ProviderHealthStatus } from "./types";

export function providerHealthStatusLabel(status: ProviderHealthStatus): string {
  if (status === "healthy") {
    return "Healthy";
  }
  if (status === "degraded") {
    return "Provider degraded";
  }
  if (status === "stale") {
    return "Data stale";
  }
  if (status === "failing") {
    return "Polling failed";
  }
  if (status === "unavailable") {
    return "Unavailable";
  }
  return "Unknown";
}

export function providerHealthReadinessLabel(snapshot: ProviderHealthSnapshot): string {
  if (snapshot.status === "healthy" && snapshot.missing_candle_count === 0) {
    return "Ready for deterministic analysis";
  }
  if (snapshot.missing_candle_count > 0) {
    return "Recovery plan needed";
  }
  if (snapshot.status === "stale") {
    return "Data stale";
  }
  if (snapshot.consecutive_failure_count > 0) {
    return "Retryable provider issue";
  }
  return "Review needed";
}

export function providerHealthTone(value: string | null | undefined) {
  const normalized = value?.toLowerCase();
  if (normalized === "healthy" || normalized === "fresh") {
    return "good" as const;
  }
  if (normalized === "delayed" || normalized === "degraded") {
    return "warning" as const;
  }
  if (normalized === "stale" || normalized === "failing" || normalized === "unavailable") {
    return "danger" as const;
  }
  return "neutral" as const;
}
