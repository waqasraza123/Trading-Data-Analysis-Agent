import type { JsonRecord, JsonValue, SignalEvidence } from "@/lib/api/types";
import { setupLabel, setupText } from "@/lib/setup-detail/labels";
import type { EvidenceGroup, SetupDetailData, SetupDetailViewModel } from "@/lib/setup-detail/types";

export function composeSetupDetail(data: SetupDetailData): SetupDetailViewModel {
  const reportSummary = recordSection(data.report?.sections.summary);
  const actionPlanSection = recordSection(data.report?.sections.action_plan);
  const humanReviewSection = recordSection(data.report?.sections.human_review);
  const signal = data.signal?.signal || null;
  const setupMetadata = data.setupContext?.metadata_json;
  const latestFinalCandleTime = latestFinalCandleTimeFromSetup(setupMetadata);
  const dataFreshness = dataFreshnessFromSetup(data.setupContext?.data_quality_warnings_json || []);

  return {
    header: {
      symbol: stringValue(reportSummary?.symbol) || shortId(signal?.symbol_id) || "Signal",
      timeframe: signal?.timeframe || data.setupContext?.timeframe || stringValue(reportSummary?.timeframe) || "Not available",
      bias: signal?.bias || data.setupContext?.directional_bias || stringValue(reportSummary?.bias) || "Not available",
      pattern: signal?.pattern_type || stringValue(reportSummary?.pattern_type) || "No pattern",
      confidenceLabel: signal?.confidence_label || stringValue(reportSummary?.confidence_label) || "Not available",
      confidenceScore: signal?.confidence_score || stringValue(reportSummary?.confidence_score),
      setupQualityLabel: data.setupContext?.setup_quality_label || "Not available",
      setupQualityScore: data.setupContext?.setup_quality_score || null,
      latestFinalCandleTime,
      dataFreshness,
      summary: firstSummary(data.setupContext?.summary, signal?.summary, signal?.no_signal_reason),
    },
    signal: data.signal,
    report: data.report,
    setupContext: data.setupContext,
    evidenceGroups: groupEvidence(data.signal?.evidence || []),
    confidenceComponents: data.signal?.confidence_components || [],
    riskNotes: data.signal?.risk_notes || [],
    outcomes: data.outcomes,
    readiness: data.readiness,
    quality: data.quality,
    historicalCases: data.historicalCases,
    reasoning: data.reasoning,
    auditTimeline: data.auditTimeline,
    marketRegime: data.marketRegime,
    marketSession: data.marketSession,
    multiTimeframeContext: data.multiTimeframeContext,
    crossAssetContext: data.crossAssetContext,
    crossAssetResults: data.crossAssetResults,
    journalEntries: data.journalEntries,
    actionPlanSection,
    humanReviewSection,
    reportMissingSections: data.report?.missing_sections || [],
    reportWarnings: data.report?.warnings || [],
    failures: data.failures,
  };
}

export function recordSection(value: JsonValue | undefined): JsonRecord | null {
  if (isRecord(value)) {
    return value;
  }
  return null;
}

export function recordArray(value: JsonValue | undefined): JsonRecord[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isRecord);
}

export function boundedSectionItems(value: JsonValue | undefined): JsonRecord[] {
  const record = recordSection(value);
  if (!record) {
    return [];
  }
  return recordArray(record.items);
}

export function stringValue(value: JsonValue | undefined): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

export function countSectionItems(value: JsonValue | undefined): number {
  const record = recordSection(value);
  if (!record) {
    return 0;
  }
  const returned = Number(record.returned_count);
  const total = Number(record.total_count);
  if (Number.isFinite(total)) {
    return total;
  }
  if (Number.isFinite(returned)) {
    return returned;
  }
  return boundedSectionItems(value).length;
}

export function itemTitle(record: JsonRecord): string {
  const value =
    stringValue(record.title) ||
    stringValue(record.label) ||
    stringValue(record.action_type) ||
    stringValue(record.finding_type) ||
    stringValue(record.code) ||
    "Context item";
  return setupLabel(value);
}

export function itemBody(record: JsonRecord): string {
  return (
    stringValue(record.message) ||
    stringValue(record.description) ||
    stringValue(record.summary) ||
    stringValue(record.reason) ||
    stringValue(record.error_message) ||
    "Structured context returned."
  );
}

function groupEvidence(evidence: SignalEvidence[]): EvidenceGroup[] {
  const groups = new Map<string, EvidenceGroup>();
  evidence.forEach((item) => {
    const type = item.evidence_type || "unknown";
    const group =
      groups.get(type) ||
      ({
        type,
        supporting: [],
        conflicting: [],
        neutral: [],
      } satisfies EvidenceGroup);
    if (item.direction === "conflict" || item.direction === "opposes" || item.direction === "opposing") {
      group.conflicting.push(item);
    } else if (item.direction === "neutral" || item.direction === "mixed") {
      group.neutral.push(item);
    } else {
      group.supporting.push(item);
    }
    groups.set(type, group);
  });
  return Array.from(groups.values()).sort((left, right) => left.type.localeCompare(right.type));
}

function latestFinalCandleTimeFromSetup(metadata: JsonRecord | undefined): string | null {
  const marketContext = recordSection(metadata?.market_context);
  const latestOutcome = Array.isArray(marketContext?.outcomes) ? marketContext.outcomes[0] : null;
  if (isRecord(latestOutcome) && typeof latestOutcome.reference_time === "string") {
    return latestOutcome.reference_time;
  }
  return null;
}

function dataFreshnessFromSetup(warnings: JsonRecord[]): string {
  const staleWarning = warnings.find((warning) => {
    const code = String(warning.code || "").toLowerCase();
    return code.includes("stale") || code.includes("freshness");
  });
  if (staleWarning) {
    return setupLabel(String(staleWarning.code || "review data freshness"));
  }
  return warnings.length ? "Review data quality" : "No freshness warning";
}

function firstSummary(...values: Array<string | null | undefined>): string {
  const value = values.find((candidate) => typeof candidate === "string" && candidate.trim());
  return value ? setupText(value) : "No setup summary returned.";
}

function shortId(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
