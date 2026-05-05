import { formatDateTime } from "@/lib/formatting/dates";
import { formatInteger, formatPercent } from "@/lib/formatting/numbers";
import { setupLabel } from "@/lib/setup-detail/labels";
import { composeSetupDetail } from "@/lib/setup-detail/composeSetupDetail";
import type { SetupDetailData } from "@/lib/setup-detail/types";
import type { SetupReviewMetric, SetupReviewModel } from "./types";

export function composeSetupReview(data: SetupDetailData): SetupReviewModel {
  const base = composeSetupDetail(data);
  const supportingEvidence = base.evidenceGroups.reduce((total, group) => total + group.supporting.length, 0);
  const conflictingEvidence = base.evidenceGroups.reduce((total, group) => total + group.conflicting.length, 0);
  const latestFinalCandle = base.setupChart.latestFinalCandle?.timestamp || base.header.latestFinalCandleTime;
  const sectionCounts = {
    supportingEvidence,
    conflictingEvidence,
    confidenceComponents: base.confidenceComponents.length,
    riskNotes: base.riskNotes.length + (base.setupContext?.risk_notes_json.length || 0),
    waitConditions: base.setupContext?.wait_conditions_json.length || 0,
    avoidReasons: base.setupContext?.avoid_reasons_json.length || 0,
    outcomes: base.outcomes.length,
    historicalCases: base.historicalCases?.results.length || 0,
    auditEvents: base.auditTimeline?.events.length || 0,
    journalEntries: base.journalEntries.length,
  };

  return {
    ...base,
    sectionCounts,
    summaryMetrics: [
      metric("Confidence", formatPercent(base.header.confidenceScore), setupLabel(base.header.confidenceLabel), "info"),
      metric("Priority", priorityLabel(base), "Human review score", "warning"),
      metric("Setup quality", formatPercent(base.header.setupQualityScore), setupLabel(base.header.setupQualityLabel), "good"),
      metric("Freshness", formatDateTime(latestFinalCandle), setupLabel(base.header.dataFreshness), latestFinalCandle ? "good" : "warning"),
      metric("Evidence", formatInteger(supportingEvidence), `${formatInteger(conflictingEvidence)} conflicting`, conflictingEvidence > 0 ? "warning" : "good"),
      metric("Journal", formatInteger(sectionCounts.journalEntries), "Linked reflections", "neutral"),
    ],
  };
}

function priorityLabel(model: ReturnType<typeof composeSetupDetail>): string {
  const priority = model.report?.sections.priority;
  if (priority && typeof priority === "object" && !Array.isArray(priority)) {
    const score = priority.priority_score;
    if (typeof score === "string" || typeof score === "number") {
      return formatPercent(String(score));
    }
  }
  return "Not available";
}

function metric(label: string, value: string, detail: string, tone: SetupReviewMetric["tone"]): SetupReviewMetric {
  return { label, value, detail, tone };
}
