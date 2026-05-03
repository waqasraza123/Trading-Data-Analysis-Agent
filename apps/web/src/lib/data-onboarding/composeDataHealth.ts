import type {
  DataHealthRow,
  DataHealthStatus,
  HealthCheckInput,
  OnboardingSummaryCounts,
} from "./types";

export function composeDataHealth(input: HealthCheckInput): DataHealthRow {
  const issues: string[] = [];
  let status: DataHealthStatus = "ready";

  if (input.errors.length > 0) {
    status = "backend_unavailable";
    issues.push("Backend unavailable");
  }

  if (!input.latestFinalCandle) {
    status = strongerStatus(status, "missing_data");
    issues.push("Missing latest final candle");
  }

  if (input.candleQuality) {
    if (input.candleQuality.missing_candles > 0) {
      status = strongerStatus(status, "recovery_needed");
      issues.push("Missing candles");
    }
    if (Number(input.candleQuality.quality_score) < 0.85) {
      status = strongerStatus(status, "degraded");
      issues.push("Data quality degraded");
    }
    if (input.candleQuality.duplicate_candles > 0) {
      status = strongerStatus(status, "degraded");
      issues.push("Duplicate candles");
    }
  }

  if (input.dataQualityRun) {
    const label = input.dataQualityRun.quality_label.toLowerCase();
    if (label === "poor" || label === "insufficient_data") {
      status = strongerStatus(status, "degraded");
      issues.push("Data quality run degraded");
    }
    if (input.dataQualityRun.finding_count > 0) {
      status = strongerStatus(status, "degraded");
      issues.push("Data quality findings present");
    }
  }

  if (input.marketMemory) {
    const freshness = input.marketMemory.freshness_label.toLowerCase();
    if (freshness === "stale" || freshness === "no_data") {
      status = strongerStatus(status, "stale");
      issues.push("Market memory stale");
    }
    const quality = input.marketMemory.data_quality_label.toLowerCase();
    if (quality === "degraded" || quality === "poor" || quality === "insufficient") {
      status = strongerStatus(status, "degraded");
      issues.push("Market memory data quality degraded");
    }
  }

  if (input.liveSubscription) {
    const liveStatus = input.liveSubscription.status.toLowerCase();
    if (liveStatus === "stale" || liveStatus === "failed" || liveStatus === "stopped") {
      status = strongerStatus(status, "stale");
      issues.push("Live feed stale");
    }
  }

  if (input.providerPollingRequest?.status.toLowerCase() === "failed") {
    status = strongerStatus(status, "degraded");
    issues.push("Provider polling failed");
  }

  return {
    ...input,
    status,
    statusLabel: statusLabel(status),
    issues: dedupeIssues(issues),
  };
}

export function summarizeDataHealth(rows: DataHealthRow[]): OnboardingSummaryCounts {
  return rows.reduce<OnboardingSummaryCounts>(
    (counts, row) => ({
      ready: counts.ready + (row.status === "ready" ? 1 : 0),
      degraded: counts.degraded + (row.status === "degraded" ? 1 : 0),
      missingData: counts.missingData + (row.status === "missing_data" ? 1 : 0),
      staleLiveFeeds: counts.staleLiveFeeds + (row.status === "stale" ? 1 : 0),
      recoveryNeeded: counts.recoveryNeeded + (row.status === "recovery_needed" ? 1 : 0),
    }),
    {
      ready: 0,
      degraded: 0,
      missingData: 0,
      staleLiveFeeds: 0,
      recoveryNeeded: 0,
    },
  );
}

function strongerStatus(current: DataHealthStatus, next: DataHealthStatus): DataHealthStatus {
  const rank: Record<DataHealthStatus, number> = {
    ready: 0,
    degraded: 1,
    stale: 2,
    missing_data: 3,
    recovery_needed: 4,
    backend_unavailable: 5,
  };
  return rank[next] > rank[current] ? next : current;
}

function statusLabel(status: DataHealthStatus): string {
  if (status === "ready") {
    return "Ready for deterministic analysis";
  }
  if (status === "stale") {
    return "Data stale";
  }
  if (status === "missing_data") {
    return "Missing candles";
  }
  if (status === "recovery_needed") {
    return "Recovery plan needed";
  }
  if (status === "backend_unavailable") {
    return "Backend unavailable";
  }
  return "Data degraded";
}

function dedupeIssues(values: string[]): string[] {
  return Array.from(new Set(values));
}
