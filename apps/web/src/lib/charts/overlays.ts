import type {
  AnalysisRun,
  JsonRecord,
  SetupContext,
  SignalOutcome,
  SignalRead,
} from "@/lib/api/types";
import { chartLabel, chartText } from "./labels";
import type {
  ChartOutcomeMarker,
  ChartOverlays,
  ChartPatternMarker,
  ChartSignalWindow,
  ChartTone,
  ChartZone,
  ChartZoneKind,
  RawZoneRecord,
} from "./types";

export function buildChartOverlays(input: {
  setupContext: SetupContext | null;
  analysisRun: AnalysisRun | null;
  signal: SignalRead | null;
  outcomes: SignalOutcome[];
  supportResistance: JsonRecord | null;
}): ChartOverlays {
  return {
    zones: [
      ...setupZones(input.setupContext),
      ...supportResistanceZones(input.supportResistance),
    ],
    signalWindow: signalWindow(input.analysisRun),
    patternMarker: patternMarker(input.signal, input.analysisRun),
    outcomeMarkers: outcomeMarkers(input.outcomes),
  };
}

export function setupZones(setupContext: SetupContext | null): ChartZone[] {
  if (!setupContext) {
    return [];
  }
  return [
    ...zoneRecords(setupContext.observation_zones_json, "observation", "Observation zone", "info"),
    ...zoneRecords(setupContext.invalidation_context_json, "invalidation", "Invalidation context", "warning"),
    ...zoneRecords(setupContext.target_context_zones_json, "target", "Target context zone", "good"),
  ];
}

export function supportResistanceZones(supportResistance: JsonRecord | null): ChartZone[] {
  if (!supportResistance) {
    return [];
  }
  const support = recordsFromValue(supportResistance.support_zones).slice(0, 3);
  const resistance = recordsFromValue(supportResistance.resistance_zones).slice(0, 3);
  const nearestSupport = recordFromValue(supportResistance.nearest_support);
  const nearestResistance = recordFromValue(supportResistance.nearest_resistance);
  return [
    ...zoneRecords(nearestSupport ? [nearestSupport] : [], "supportResistance", "Nearest support context", "neutral"),
    ...zoneRecords(nearestResistance ? [nearestResistance] : [], "supportResistance", "Nearest resistance context", "neutral"),
    ...zoneRecords(support, "supportResistance", "Support context", "neutral"),
    ...zoneRecords(resistance, "supportResistance", "Resistance context", "neutral"),
  ];
}

export function signalWindow(analysisRun: AnalysisRun | null): ChartSignalWindow | null {
  if (!analysisRun) {
    return null;
  }
  return {
    start: analysisRun.start_time,
    end: analysisRun.end_time,
    label: "Signal window",
  };
}

export function patternMarker(signal: SignalRead | null, analysisRun: AnalysisRun | null): ChartPatternMarker | null {
  if (!signal && !analysisRun) {
    return null;
  }
  return {
    timestamp: analysisRun?.end_time || signal?.created_at || null,
    label: "Review marker",
    detail: chartLabel(signal?.pattern_type || "No pattern"),
  };
}

export function outcomeMarkers(outcomes: SignalOutcome[]): ChartOutcomeMarker[] {
  return outcomes.slice(0, 8).map((outcome) => {
    const kind: ChartOutcomeMarker["kind"] = outcome.reversal_detected
      ? "reversal"
      : outcome.direction_followed
      ? "followThrough"
      : outcome.outcome_label === "insufficient_data"
      ? "insufficient"
      : "noFollowThrough";
    return {
      id: outcome.id,
      timestamp: outcome.future_window_end || outcome.reference_time,
      label: outcomeLabel(kind),
      detail: `${outcome.horizon_minutes}m horizon`,
      kind,
    };
  });
}

function zoneRecords(
  records: JsonRecord[],
  kind: ChartZoneKind,
  fallbackLabel: string,
  tone: ChartTone,
): ChartZone[] {
  return records
    .map((record, index) => zoneFromRecord(record as RawZoneRecord, kind, fallbackLabel, tone, index))
    .filter((zone): zone is ChartZone => zone !== null);
}

function zoneFromRecord(
  record: RawZoneRecord,
  kind: ChartZoneKind,
  fallbackLabel: string,
  tone: ChartTone,
  index: number,
): ChartZone | null {
  const lower = numericValue(record.lower);
  const upper = numericValue(record.upper);
  const midpoint = numericValue(record.midpoint);
  const level = numericValue(record.level) ?? numericValue(record.price) ?? midpoint;
  if (![lower, upper, level].some((value) => Number.isFinite(value))) {
    return null;
  }
  const zoneType = stringField(record, "zoneType", "zone_type");
  const role = stringField(record, "role");
  const source = stringField(record, "source");
  const detail = detailFromRecord(record);
  return {
    id: `${kind}-${fallbackLabel}-${index}-${lower ?? ""}-${upper ?? ""}-${level ?? ""}`,
    label: chartLabel(role || zoneType || fallbackLabel),
    detail,
    kind,
    tone,
    lower,
    upper,
    level,
    source: source ? chartLabel(source) : null,
  };
}

function outcomeLabel(kind: ChartOutcomeMarker["kind"]): string {
  if (kind === "followThrough") {
    return "Observed follow-through";
  }
  if (kind === "reversal") {
    return "Observed reversal";
  }
  if (kind === "insufficient") {
    return "Insufficient outcome data";
  }
  return "No follow-through observed";
}

function detailFromRecord(record: RawZoneRecord): string | null {
  const condition = chartText(record.condition, "");
  const confidence = chartText(record.confidence, "");
  const source = chartText(record.source, "");
  const parts = [condition, confidence ? `Confidence: ${confidence}` : "", source ? `Source: ${source}` : ""].filter(Boolean);
  return parts.length ? parts.join(" | ") : null;
}

function recordsFromValue(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function recordFromValue(value: unknown): JsonRecord | null {
  return isRecord(value) ? value : null;
}

function numericValue(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function stringField(record: JsonRecord, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
