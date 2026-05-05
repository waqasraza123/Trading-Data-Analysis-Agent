import { buildCandleSlots, expandWindowAroundSignal, latestFinalCandle, normalizeChartCandles } from "@/lib/charts/candles";
import { buildChartOverlays } from "@/lib/charts/overlays";
import type {
  ChartBadge,
  ChartCandle,
  ChartCandleSlot,
  ChartOverlays,
  ChartWarning,
} from "@/lib/charts/types";
import type { CandleQualityReport } from "@/lib/data-onboarding/types";
import { getCandleQuality, getLatestCandle, listCandles } from "./candles";
import { apiGet } from "./client";
import type {
  AdvancedFeatureSnapshot,
  AnalysisRun,
  ApiFailure,
  ApiResult,
  JsonRecord,
  SetupContext,
  SignalClassification,
  SignalOutcome,
  UUID,
} from "./types";

export type SetupChartFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type SetupChartContext = {
  status: "ready" | "empty" | "unavailable";
  analysisRun: AnalysisRun | null;
  candles: ChartCandle[];
  slots: ChartCandleSlot[];
  latestFinalCandle: ChartCandle | null;
  candleQuality: CandleQualityReport | null;
  advancedFeatures: AdvancedFeatureSnapshot | null;
  overlays: ChartOverlays;
  badges: ChartBadge[];
  warnings: ChartWarning[];
  failures: SetupChartFailure[];
  window: {
    startTime: string | null;
    endTime: string | null;
  };
};

type SetupChartInput = {
  signalId: UUID;
  signal: SignalClassification | null;
  setupContext: SetupContext | null;
  outcomes: SignalOutcome[];
};

export async function getSetupChartContext(input: SetupChartInput): Promise<SetupChartContext> {
  const signal = input.signal?.signal || null;
  const failures: SetupChartFailure[] = [];

  if (!signal) {
    return emptyChartContext({
      status: "unavailable",
      failures: [
        {
          label: "Signal chart context",
          status: 0,
          message: "Signal payload is required before candle context can be loaded.",
          missing: true,
        },
      ],
    });
  }

  const analysisRunResult = await getAnalysisRun(signal.analysis_run_id);
  const analysisRun = readNullableResult("Analysis run", analysisRunResult, failures);
  const window = expandWindowAroundSignal(
    analysisRun?.start_time || analysisRun?.lookback_start || signal.created_at,
    analysisRun?.end_time || analysisRun?.lookback_end || signal.created_at,
    signal.timeframe,
    140,
  );

  if (!window) {
    return emptyChartContext({
      status: "unavailable",
      analysisRun,
      failures,
      warnings: [{ code: "chart_window_unavailable", message: "Chart window could not be inferred from the signal." }],
    });
  }

  const sourceId = analysisRun?.source_id || null;
  const [candlesResult, latestResult, qualityResult, advancedFeaturesResult] = await Promise.all([
    listCandles({
      workspaceId: signal.workspace_id,
      symbolId: signal.symbol_id,
      sourceId,
      timeframe: signal.timeframe,
      startTime: window.startTime,
      endTime: window.endTime,
      limit: 200,
    }),
    getLatestCandle({
      workspaceId: signal.workspace_id,
      symbolId: signal.symbol_id,
      sourceId,
      timeframe: signal.timeframe,
      isFinal: true,
    }),
    getCandleQuality({
      workspaceId: signal.workspace_id,
      symbolId: signal.symbol_id,
      sourceId,
      timeframe: signal.timeframe,
      startTime: window.startTime,
      endTime: window.endTime,
    }),
    getSignalAdvancedFeatures(input.signalId),
  ]);

  const rawCandles = readResult("Final candles", candlesResult, [], failures);
  const candleQuality = readNullableResult("Candle quality", qualityResult, failures);
  const advancedFeatures = readNullableResult("Advanced price-action context", advancedFeaturesResult, failures);
  const candles = normalizeChartCandles(rawCandles);
  const slots = buildCandleSlots(candles, signal.timeframe, 220);
  const fallbackLatest = latestResult.ok ? normalizeChartCandles([latestResult.data])[0] || null : null;
  if (!latestResult.ok) {
    failures.push(toFailure("Latest final candle", latestResult));
  }

  const latest = fallbackLatest || latestFinalCandle(candles);
  const overlays = buildChartOverlays({
    setupContext: input.setupContext,
    analysisRun,
    signal,
    outcomes: input.outcomes,
    supportResistance: advancedFeatures?.support_resistance_json || null,
  });
  const warnings = chartWarnings({
    candles,
    candleQuality,
    setupContext: input.setupContext,
    advancedFeatures,
  });

  return {
    status: candles.length > 0 ? "ready" : "empty",
    analysisRun,
    candles,
    slots,
    latestFinalCandle: latest,
    candleQuality,
    advancedFeatures,
    overlays,
    badges: chartBadges({
      setupContext: input.setupContext,
      candleQuality,
      latest,
      candles,
    }),
    warnings,
    failures,
    window,
  };
}

function getAnalysisRun(analysisRunId: UUID): Promise<ApiResult<AnalysisRun>> {
  return apiGet<AnalysisRun>(`/analysis-runs/${analysisRunId}`, { optional: true });
}

function getSignalAdvancedFeatures(signalId: UUID): Promise<ApiResult<AdvancedFeatureSnapshot>> {
  return apiGet<AdvancedFeatureSnapshot>(`/signals/${signalId}/advanced-features`, { optional: true });
}

function chartBadges(input: {
  setupContext: SetupContext | null;
  candleQuality: CandleQualityReport | null;
  latest: ChartCandle | null;
  candles: ChartCandle[];
}): ChartBadge[] {
  const qualityLabel = input.setupContext?.setup_quality_label || "Context unavailable";
  const dataQualityScore = Number(input.candleQuality?.quality_score);
  const dataQualityValue = Number.isFinite(dataQualityScore)
    ? `${Math.round(dataQualityScore * 100)}% data quality`
    : "Data quality unavailable";
  return [
    { label: "Setup quality", value: qualityLabel, tone: toneForValue(qualityLabel) },
    {
      label: "Freshness",
      value: input.latest ? "Latest final candle loaded" : "Latest final candle unavailable",
      tone: input.latest ? "good" : "warning",
    },
    {
      label: "Data quality",
      value: dataQualityValue,
      tone: dataQualityScore >= 0.85 ? "good" : dataQualityScore >= 0.65 ? "warning" : "neutral",
    },
    { label: "Candles", value: `${input.candles.length} final candles`, tone: input.candles.length ? "info" : "warning" },
  ];
}

function chartWarnings(input: {
  candles: ChartCandle[];
  candleQuality: CandleQualityReport | null;
  setupContext: SetupContext | null;
  advancedFeatures: AdvancedFeatureSnapshot | null;
}): ChartWarning[] {
  const warnings: ChartWarning[] = [];
  if (input.candles.length === 0) {
    warnings.push({ code: "no_candles", message: "No final candles were returned for this chart window." });
  }
  if (input.candleQuality && input.candleQuality.missing_candles > 0) {
    warnings.push({
      code: "missing_candles",
      message: `${input.candleQuality.missing_candles} expected final candles are missing in this chart window.`,
    });
  }
  input.setupContext?.data_quality_warnings_json.slice(0, 3).forEach((warning) => {
    warnings.push({
      code: String(warning.code || "setup_data_quality"),
      message: String(warning.message || warning.reason || "Setup context reported a data-quality warning."),
    });
  });
  const advancedWarnings = input.advancedFeatures?.warnings_json;
  Object.entries(advancedWarnings || {}).slice(0, 3).forEach(([code, value]) => {
    warnings.push({
      code,
      message: typeof value === "string" ? value : "Advanced context returned a chart warning.",
    });
  });
  return warnings;
}

function toneForValue(value: string): ChartBadge["tone"] {
  const normalized = value.toLowerCase();
  if (["strong", "fresh", "healthy", "ready"].includes(normalized)) {
    return "good";
  }
  if (["weak", "stale", "degraded"].includes(normalized)) {
    return "warning";
  }
  if (["failed", "unhealthy"].includes(normalized)) {
    return "danger";
  }
  return "info";
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: SetupChartFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readNullableResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: SetupChartFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return null;
}

function toFailure(label: string, result: ApiFailure): SetupChartFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.missing ? "Endpoint not available yet" : result.error.message,
    missing: result.error.missing,
  };
}

function emptyChartContext(partial: Partial<SetupChartContext> = {}): SetupChartContext {
  return {
    status: partial.status || "empty",
    analysisRun: partial.analysisRun || null,
    candles: [],
    slots: [],
    latestFinalCandle: null,
    candleQuality: null,
    advancedFeatures: null,
    overlays: {
      zones: [],
      signalWindow: null,
      patternMarker: null,
      outcomeMarkers: [],
    },
    badges: [],
    warnings: partial.warnings || [],
    failures: partial.failures || [],
    window: partial.window || { startTime: null, endTime: null },
  };
}
