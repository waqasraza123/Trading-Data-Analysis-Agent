import { apiGet } from "./client";
import type { ApiResult, AuditTimeline, IntelligenceReport, UUID } from "./types";

export function getSignalReport(signalId: UUID): Promise<ApiResult<IntelligenceReport>> {
  return apiGet<IntelligenceReport>(`/intelligence-reports/signals/${signalId}`, {
    query: {
      includeAudit: true,
      includeReasoning: true,
      includeActions: true,
      includeOutcomes: true,
      includeDiagnostics: true,
      limitAudit: 100,
      limitEvidence: 50,
    },
    optional: true,
  });
}

export function getSignalAuditTimeline(signalId: UUID): Promise<ApiResult<AuditTimeline>> {
  return apiGet<AuditTimeline>(`/audit-timeline/signals/${signalId}`, {
    query: {
      includeAudit: true,
      includeGraph: true,
      includeArtifacts: true,
      limitEvents: 100,
    },
    optional: true,
  });
}
