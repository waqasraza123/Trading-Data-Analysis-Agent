import { getPublicEnv } from "@/config/env";
import { classifyTriage } from "@/lib/triage/classifyTriage";
import type {
  IntelligenceQualityResponse,
  OperatorReviewItem,
  ScenarioReasoningResponse,
  TriageActionItem,
  TriageBoardData,
  TriageCandidate,
  TriageFailure,
  TriageFilterState,
} from "@/lib/triage/types";
import { apiGet } from "./client";
import { listMarketMemorySnapshots, listSymbols, listWorkspaces } from "./market";
import { listSignalOutcomes } from "./outcomes";
import {
  getDefaultPreferenceProfile,
  getPreferenceProfile,
  listPreferenceProfiles,
  matchPreferenceProfileSignal,
} from "./preferenceProfiles";
import { getLatestSignalReadiness } from "./readiness";
import { listSignalCardReadModels } from "./readModels";
import { getSignalReport } from "./reports";
import { getSignalPriorityScore } from "./signal-priority";
import { getAnalysisRunSignal, getSignal } from "./signals";
import { getSignalSetupContext } from "./setup-context";
import type {
  AnalysisRun,
  ApiFailure,
  ApiResult,
  MarketMemorySnapshot,
  SignalCardReadModel,
  SignalClassification,
  SignalPriorityScore,
  UUID,
} from "./types";
import type { PreferenceProfile } from "@/lib/preferences/types";

const signalCandidateLimit = 48;

export async function getSignalTriageBoard(params: Record<string, string | undefined>): Promise<TriageBoardData> {
  const env = getPublicEnv();
  const filters = parseTriageFilters(params);
  const failures: TriageFailure[] = [];
  const [workspacesResult, symbolsResult] = await Promise.all([listWorkspaces(), listSymbols()]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const workspace = workspaces.find((candidate) => candidate.id === filters.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: filters.workspaceId || null,
      workspace: null,
      workspaces,
      symbols,
      preferenceProfiles: [],
      selectedPreferenceProfile: null,
      filters,
      candidates: [],
      allCandidates: [],
      unfilteredCandidateCount: 0,
      failures,
      lastLoadedAt: new Date().toISOString(),
    };
  }

  const resolvedFilters = { ...filters, workspaceId: workspace.id };
  const [
    memoryResult,
    analysisRunsResult,
    actionItemsResult,
    reviewsResult,
    preferenceProfilesResult,
    selectedPreferenceProfileResult,
  ] = await Promise.all([
    listMarketMemorySnapshots(workspace.id),
    listAnalysisRunsForTriage(workspace.id),
    listDueActionItemsForTriage(workspace.id),
    listOperatorReviewsForTriage(workspace.id),
    listPreferenceProfiles({ workspaceId: workspace.id }),
    filters.preferenceProfileId
      ? getPreferenceProfile(filters.preferenceProfileId)
      : getDefaultPreferenceProfile(workspace.id),
  ]);
  const memorySnapshots = readResult("Market memory", memoryResult, [], failures);
  const analysisRuns = readResult("Analysis runs", analysisRunsResult, [], failures);
  const actionItems = readResult("Backend action items", actionItemsResult, [], failures);
  const reviews = readResult("Operator reviews", reviewsResult, [], failures);
  const preferenceProfiles = readOptionalBaseList("Preference profiles", preferenceProfilesResult, failures);
  const selectedPreferenceProfile = readOptionalBaseResult(
    filters.preferenceProfileId ? "Selected preference profile" : "Default preference profile",
    selectedPreferenceProfileResult,
    failures,
  );
  const readModelResult = await listSignalCardReadModels({
    workspaceId: workspace.id,
    symbolId: filters.symbolId,
    timeframe: filters.timeframe,
    bias: filters.bias,
    freshnessLabel: filters.freshness,
    limit: signalCandidateLimit,
    offset: 0,
  });
  const readModelCards = readModelResult.ok ? readModelResult.data : [];
  if (readModelCards.length > 0) {
    const symbolMap = new Map(symbols.map((symbol) => [symbol.id, symbol]));
    const readModelCandidates = readModelCards.map((card) =>
      candidateFromReadModel(card, symbolMap.get(card.symbol_id) || null),
    );
    const preferenceScopedCandidates = await applyPreferenceProfileFilter(
      readModelCandidates,
      selectedPreferenceProfile,
      failures,
    );
    const candidates = preferenceScopedCandidates.filter((candidate) =>
      matchesFilters(candidate, resolvedFilters),
    );
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: filters.workspaceId || null,
      workspace,
      workspaces,
      symbols,
      preferenceProfiles,
      selectedPreferenceProfile,
      filters: {
        ...resolvedFilters,
        preferenceProfileId: selectedPreferenceProfile?.id || filters.preferenceProfileId,
      },
      candidates: sortCandidates(candidates, resolvedFilters.sort),
      allCandidates: sortCandidates(preferenceScopedCandidates, resolvedFilters.sort),
      unfilteredCandidateCount: readModelCandidates.length,
      failures,
      lastLoadedAt: new Date().toISOString(),
    };
  }
  if (!readModelResult.ok && !readModelResult.error.missing) {
    failures.push(toFailure("Signal card read models", readModelResult));
  }
  const signalRefs = await resolveSignalRefs(memorySnapshots, analysisRuns, failures);
  const symbolMap = new Map(symbols.map((symbol) => [symbol.id, symbol]));
  const memoryBySignalId = new Map<UUID, MarketMemorySnapshot>();
  for (const snapshot of memorySnapshots) {
    if (snapshot.latest_signal_id) {
      memoryBySignalId.set(snapshot.latest_signal_id, snapshot);
    }
  }
  const allCandidates = await Promise.all(
    signalRefs.slice(0, signalCandidateLimit).map(async (signal) => {
      const memory = memoryBySignalId.get(signal.signal.id) || null;
      const candidateActionItems = actionItems.filter(
        (item) => item.signal_id === signal.signal.id || item.analysis_run_id === signal.analysis_run_id,
      );
      const candidateReviews = reviews.filter(
        (item) => item.related_signal_id === signal.signal.id || item.related_analysis_run_id === signal.analysis_run_id,
      );
      return enrichCandidate(
        signal,
        symbolMap.get(signal.signal.symbol_id) || null,
        memory,
        candidateActionItems,
        candidateReviews,
        failures,
      );
    }),
  );

  const preferenceScopedCandidates = await applyPreferenceProfileFilter(
    allCandidates,
    selectedPreferenceProfile,
    failures,
  );
  const candidates = preferenceScopedCandidates.filter((candidate) =>
    matchesFilters(candidate, resolvedFilters),
  );

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace,
    workspaces,
    symbols,
    preferenceProfiles,
    selectedPreferenceProfile,
    filters: {
      ...resolvedFilters,
      preferenceProfileId: selectedPreferenceProfile?.id || filters.preferenceProfileId,
    },
    candidates: sortCandidates(candidates, resolvedFilters.sort),
    allCandidates: sortCandidates(preferenceScopedCandidates, resolvedFilters.sort),
    unfilteredCandidateCount: allCandidates.length,
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

function candidateFromReadModel(
  card: SignalCardReadModel,
  symbol: TriageCandidate["symbol"],
): TriageCandidate {
  const signal = signalFromReadModel(card);
  const memory = memoryFromReadModel(card);
  const priorityScore = priorityFromReadModel(card);
  const setupContext = setupContextFromReadModel(card);
  const readiness = card.readiness_label
    ? {
        assessment: {
          readiness_score: 0,
          readiness_label: card.readiness_label,
          summary: card.readiness_label,
        },
        blockers: [],
        warnings: [],
        next_steps: [],
      }
    : null;
  const actionItems = actionItemsFromReadModel(card);
  const missingContexts: string[] = [];
  const input = {
    signal,
    memory,
    priorityScore,
    setupContext,
    outcomes: [],
    readiness,
    report: null,
    quality: null,
    reasoning: null,
    reviews: [],
    actionItems,
    missingContexts,
  };
  return {
    id: card.signal_id,
    symbol,
    classification: classifyTriage(input),
    ...input,
  };
}

function signalFromReadModel(card: SignalCardReadModel): SignalClassification {
  return {
    analysis_run_id: card.analysis_run_id,
    signal: {
      id: card.signal_id,
      analysis_run_id: card.analysis_run_id,
      workspace_id: card.workspace_id,
      symbol_id: card.symbol_id,
      timeframe: card.timeframe,
      strategy_profile_id: null,
      strategy_profile_key: null,
      strategy_profile_version: null,
      strategy_profile_snapshot_json: null,
      bias: card.bias,
      pattern_type: card.pattern_type,
      classification_status: card.classification_status,
      confidence_score: card.confidence_score || "0",
      confidence_label: card.confidence_label || "low",
      candidate_strength: null,
      selected_pattern_candidate_id: null,
      pips_moved: null,
      tick_moved: null,
      movement_direction: null,
      movement_quality: null,
      volatility_state: null,
      trend_state: null,
      range_state: null,
      summary: card.searchable_text,
      no_signal_reason: null,
      created_at: card.created_at,
    },
    confidence_components: [],
    evidence: [],
    risk_notes: [],
    deterministic_explanation: null,
    news_correlations: [],
    llm_explanation: null,
  };
}

function memoryFromReadModel(card: SignalCardReadModel): MarketMemorySnapshot | null {
  if (!card.freshness_label && !card.data_quality_label) {
    return null;
  }
  return {
    id: card.id,
    workspace_id: card.workspace_id,
    symbol_id: card.symbol_id,
    source_id: null,
    timeframe: card.timeframe,
    state_version: card.read_model_version,
    latest_final_candle_time: null,
    latest_analysis_run_id: card.analysis_run_id,
    latest_signal_id: card.signal_id,
    latest_outcome_id: null,
    data_quality_label: card.data_quality_label || "unknown",
    freshness_label: card.freshness_label || "unknown",
    trend_state: null,
    volatility_state: null,
    range_state: null,
    market_regime_label: null,
    market_session_label: null,
    multi_timeframe_label: null,
    cross_asset_label: null,
    latest_signal_bias: card.bias,
    latest_signal_pattern_type: card.pattern_type,
    latest_signal_confidence_label: card.confidence_label,
    context_json: {},
    warnings_json: readJsonArray(card.warning_summary_json.items),
    created_at: card.created_at,
    updated_at: card.updated_at,
  };
}

function priorityFromReadModel(card: SignalCardReadModel): SignalPriorityScore | null {
  if (!card.priority_label && !card.review_bucket && !card.priority_score) {
    return null;
  }
  return {
    id: card.id,
    workspace_id: card.workspace_id,
    signal_id: card.signal_id,
    analysis_run_id: card.analysis_run_id,
    symbol_id: card.symbol_id,
    timeframe: card.timeframe,
    priority_version: card.read_model_version,
    priority_score: card.priority_score || "0",
    priority_label: card.priority_label || "low",
    review_bucket: card.review_bucket || "review_required",
    component_scores_json: {},
    penalties_json: [],
    boosters_json: [],
    reasons_json: [],
    warnings_json: readJsonArray(card.warning_summary_json.items),
    created_at: card.created_at,
    updated_at: card.updated_at,
  };
}

function setupContextFromReadModel(card: SignalCardReadModel): TriageCandidate["setupContext"] {
  if (!card.setup_quality_label) {
    return null;
  }
  return {
    id: card.id,
    workspace_id: card.workspace_id,
    signal_id: card.signal_id,
    analysis_run_id: card.analysis_run_id,
    symbol_id: card.symbol_id,
    timeframe: card.timeframe,
    context_version: card.read_model_version,
    status: "completed",
    directional_bias: card.bias,
    setup_quality_label: card.setup_quality_label,
    setup_quality_score: "0",
    invalidation_context_json: [],
    observation_zones_json: [],
    target_context_zones_json: [],
    wait_conditions_json: [],
    avoid_reasons_json: [],
    timeframe_agreement_json: {},
    data_quality_warnings_json: readJsonArray(card.warning_summary_json.items),
    risk_notes_json: readJsonArray(card.risk_summary_json.items),
    next_observations_json: [],
    summary: card.searchable_text,
    metadata_json: {},
    created_at: card.created_at,
    updated_at: card.updated_at,
  };
}

function actionItemsFromReadModel(card: SignalCardReadModel): TriageActionItem[] {
  const items = readJsonArray(card.action_summary_json.items);
  return items.map((item, index) => ({
    id: typeof item.id === "string" ? item.id : `${card.signal_id}-${index}`,
    workspace_id: card.workspace_id,
    signal_id: card.signal_id,
    analysis_run_id: card.analysis_run_id,
    reasoning_run_id: null,
    action_type: typeof item.actionType === "string" ? item.actionType : "request_human_review",
    status: typeof item.status === "string" ? item.status : "pending",
    priority: typeof item.priority === "string" ? item.priority : "normal",
    due_at: typeof item.dueAt === "string" ? item.dueAt : null,
  }));
}

function readJsonArray(value: unknown): Array<Record<string, string | number | boolean | null>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, string | number | boolean | null> =>
        Boolean(item) && typeof item === "object" && !Array.isArray(item),
      )
    : [];
}

function parseTriageFilters(params: Record<string, string | undefined>): TriageFilterState {
  return {
    workspaceId: params.workspaceId,
    symbolSearch: normalizeSearch(params.symbolSearch || params.search),
    symbolId: params.symbolId,
    timeframe: params.timeframe,
    bias: params.bias,
    confidence: params.confidence,
    column: parseColumn(params.column),
    freshness: params.freshness,
    profileKey: params.profileKey,
    preferenceProfileId: params.preferenceProfileId,
    sort: parseSort(params.sort),
    onlyFresh: parseBoolean(params.onlyFresh),
    onlyReviewRequired: parseBoolean(params.onlyReviewRequired),
  };
}

function parseColumn(value: string | undefined): TriageFilterState["column"] {
  const columns: Array<NonNullable<TriageFilterState["column"]>> = [
    "high_quality_context",
    "needs_confirmation",
    "conflicted",
    "avoid_no_directional_signal",
    "stale_data_issue",
    "review_required",
  ];
  return columns.find((column) => column === value);
}

function parseBoolean(value: string | undefined): boolean {
  return value === "1" || value === "true" || value === "on";
}

function parseSort(value: string | undefined): TriageFilterState["sort"] {
  const sorts: Array<NonNullable<TriageFilterState["sort"]>> = ["priority", "freshness", "confidence", "created"];
  return sorts.find((sort) => sort === value) || "priority";
}

function normalizeSearch(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed || undefined;
}

async function resolveSignalRefs(
  memorySnapshots: MarketMemorySnapshot[],
  analysisRuns: AnalysisRun[],
  failures: TriageFailure[],
): Promise<SignalClassification[]> {
  const signalIds = uniqueValues(memorySnapshots.map((snapshot) => snapshot.latest_signal_id).filter(isPresent));
  const signalResults = await Promise.all(signalIds.map((signalId) => getSignal(signalId)));
  const signals = signalResults.flatMap((result, index) => {
    if (result.ok) {
      return [result.data];
    }
    failures.push(toFailure(`Signal ${signalIds[index]}`, result));
    return [];
  });
  const knownSignalIds = new Set(signals.map((signal) => signal.signal.id));
  const analysisSignals = await Promise.all(
    analysisRuns.slice(0, signalCandidateLimit).map(async (run) => {
      const result = await getAnalysisRunSignal(run.id);
      if (result.ok) {
        return knownSignalIds.has(result.data.signal.id) ? null : result.data;
      }
      if (!result.error.missing) {
        failures.push(toFailure(`Analysis run signal ${run.id}`, result));
      }
      return null;
    }),
  );
  return [...signals, ...analysisSignals.filter(isPresent)];
}

async function enrichCandidate(
  signal: SignalClassification,
  symbol: TriageCandidate["symbol"],
  memory: MarketMemorySnapshot | null,
  actionItems: TriageActionItem[],
  reviews: OperatorReviewItem[],
  failures: TriageFailure[],
): Promise<TriageCandidate> {
  const missingContexts: string[] = [];
  const [
    setupContextResult,
    outcomesResult,
    readinessResult,
    reportResult,
    qualityResult,
    reasoningResult,
    priorityResult,
  ] = await Promise.all([
    getSignalSetupContext(signal.signal.id),
    listSignalOutcomes(signal.signal.id),
    getLatestSignalReadiness(signal.signal.id),
    getSignalReport(signal.signal.id),
    getSignalQuality(signal.signal.id),
    getLatestSignalReasoning(signal.signal.id),
    getSignalPriorityScore(signal.signal.id),
  ]);
  const setupContext = readOptionalResult("Setup context", setupContextResult, missingContexts, failures);
  const outcomes = readOptionalList("Outcomes", outcomesResult, missingContexts, failures);
  const readiness = readOptionalResult("Readiness", readinessResult, missingContexts, failures);
  const report = readOptionalResult("Intelligence report", reportResult, missingContexts, failures);
  const quality = readOptionalResult("Quality gates", qualityResult, missingContexts, failures);
  const reasoning = readOptionalResult("Reasoning", reasoningResult, missingContexts, failures);
  const priorityScore = readOptionalPriorityResult("Priority score", priorityResult, failures);
  const input = {
    signal,
    memory,
    priorityScore,
    setupContext,
    outcomes,
    readiness,
    report,
    quality,
    reasoning,
    reviews,
    actionItems,
    missingContexts,
  };
  return {
    id: signal.signal.id,
    symbol,
    classification: classifyTriage(input),
    ...input,
  };
}

function listAnalysisRunsForTriage(workspaceId: UUID): Promise<ApiResult<AnalysisRun[]>> {
  return apiGet<AnalysisRun[]>("/analysis-runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 100,
      offset: 0,
    },
  });
}

function getSignalQuality(signalId: UUID): Promise<ApiResult<IntelligenceQualityResponse>> {
  return apiGet<IntelligenceQualityResponse>(`/intelligence-quality/signals/${signalId}/latest`, { optional: true });
}

function getLatestSignalReasoning(signalId: UUID): Promise<ApiResult<ScenarioReasoningResponse>> {
  return apiGet<ScenarioReasoningResponse>(`/signals/${signalId}/reasoning/scenarios/latest`, { optional: true });
}

function listOperatorReviewsForTriage(workspaceId: UUID): Promise<ApiResult<OperatorReviewItem[]>> {
  return apiGet<OperatorReviewItem[]>("/operator-reviews", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 500,
      offset: 0,
    },
  });
}

function listDueActionItemsForTriage(workspaceId: UUID): Promise<ApiResult<TriageActionItem[]>> {
  return apiGet<TriageActionItem[]>("/action-items/due", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 500,
    },
  });
}

function matchesFilters(candidate: TriageCandidate, filters: TriageFilterState): boolean {
  return (
    matchesSymbolSearch(candidate, filters.symbolSearch) &&
    matches(candidate.signal.signal.symbol_id, filters.symbolId) &&
    matches(candidate.signal.signal.timeframe, filters.timeframe) &&
    matches(candidate.signal.signal.bias, filters.bias) &&
    matches(candidate.signal.signal.confidence_label, filters.confidence) &&
    matches(candidate.classification.column, filters.column) &&
    matches(candidate.memory?.freshness_label, filters.freshness) &&
    matches(candidate.signal.signal.strategy_profile_key, filters.profileKey) &&
    (!filters.onlyFresh || candidate.memory?.freshness_label === "fresh") &&
    (!filters.onlyReviewRequired || candidate.classification.column === "review_required")
  );
}

function matchesSymbolSearch(candidate: TriageCandidate, search: string | undefined): boolean {
  if (!search) {
    return true;
  }
  const needle = search.toLowerCase();
  return [
    candidate.symbol?.symbol,
    candidate.symbol?.display_name,
    candidate.signal.signal.symbol_id,
  ].some((value) => value?.toLowerCase().includes(needle));
}

async function applyPreferenceProfileFilter(
  candidates: TriageCandidate[],
  profile: PreferenceProfile | null,
  failures: TriageFailure[],
): Promise<TriageCandidate[]> {
  if (!profile) {
    return candidates;
  }
  const matchResults = await Promise.all(
    candidates.map(async (candidate) => ({
      candidate,
      result: await matchPreferenceProfileSignal(profile.id, candidate.signal.signal.id),
    })),
  );
  let matchEndpointUnavailable = false;
  const scopedCandidates: TriageCandidate[] = [];
  for (const { candidate, result } of matchResults) {
    if (result.ok) {
      if (result.data.matches) {
        scopedCandidates.push(candidate);
      }
      continue;
    }
    if (result.error.missing) {
      matchEndpointUnavailable = true;
      continue;
    }
    failures.push(toFailure("Preference profile match", result));
  }
  if (matchEndpointUnavailable) {
    return candidates;
  }
  return scopedCandidates;
}

function sortCandidates(candidates: TriageCandidate[], sort: TriageFilterState["sort"] = "priority"): TriageCandidate[] {
  const columnOrder = [
    "review_required",
    "stale_data_issue",
    "conflicted",
    "needs_confirmation",
    "high_quality_context",
    "avoid_no_directional_signal",
  ];
  return [...candidates].sort((left, right) => {
    if (sort === "freshness") {
      const freshnessDelta = latestTime(right).localeCompare(latestTime(left));
      if (freshnessDelta !== 0) {
        return freshnessDelta;
      }
    }
    if (sort === "confidence") {
      const confidenceDelta = confidenceValue(right) - confidenceValue(left);
      if (confidenceDelta !== 0) {
        return confidenceDelta;
      }
    }
    if (sort === "created") {
      const createdDelta = right.signal.signal.created_at.localeCompare(left.signal.signal.created_at);
      if (createdDelta !== 0) {
        return createdDelta;
      }
    }
    const priorityDelta = priorityValue(right) - priorityValue(left);
    if (priorityDelta !== 0) {
      return priorityDelta;
    }
    const columnDelta = columnOrder.indexOf(left.classification.column) - columnOrder.indexOf(right.classification.column);
    if (columnDelta !== 0) {
      return columnDelta;
    }
    return latestTime(right).localeCompare(latestTime(left));
  });
}

function priorityValue(candidate: TriageCandidate): number {
  const value = Number(candidate.priorityScore?.priority_score);
  return Number.isFinite(value) ? value : -1;
}

function confidenceValue(candidate: TriageCandidate): number {
  const value = Number(candidate.signal.signal.confidence_score);
  return Number.isFinite(value) ? value : -1;
}

function latestTime(candidate: TriageCandidate): string {
  return candidate.memory?.latest_final_candle_time || candidate.signal.signal.created_at || "";
}

function matches(value: string | null | undefined, filter: string | undefined): boolean {
  return !filter || value === filter;
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: TriageFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readOptionalResult<T>(
  label: string,
  result: ApiResult<T>,
  missingContexts: string[],
  failures: TriageFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  missingContexts.push(label);
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function readOptionalList<T>(
  label: string,
  result: ApiResult<T[]>,
  missingContexts: string[],
  failures: TriageFailure[],
): T[] {
  if (result.ok) {
    return result.data;
  }
  missingContexts.push(label);
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return [];
}

function readOptionalPriorityResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: TriageFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing && result.error.status !== 0) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function readOptionalBaseResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: TriageFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function readOptionalBaseList<T>(
  label: string,
  result: ApiResult<T[]>,
  failures: TriageFailure[],
): T[] {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return [];
}

function toFailure(label: string, result: ApiFailure): TriageFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}

function uniqueValues<T>(values: T[]): T[] {
  return Array.from(new Set(values));
}

function isPresent<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}
