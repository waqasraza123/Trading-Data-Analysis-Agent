import { apiGet, apiPatch, apiPost } from "./client";
import { getPublicEnv } from "@/config/env";
import {
  journalFailure,
  type JournalData,
  type JournalDecisionType,
  type JournalEntryContext,
  type JournalEntryReview,
  type JournalEntryUpdateRequest,
  type JournalFailure,
  type JournalFilters,
  type JournalReviewCreateRequest,
  type JournalStatus,
} from "@/lib/journal/types";
import { listAnalysisRuns, listSymbols, listWorkspaces } from "./market";
import { listSignalOutcomes } from "./outcomes";
import type { ApiResult, JournalEntry, JournalEntryCreateRequest, SignalOutcome, UUID } from "./types";

export function listJournalEntries(params: {
  workspaceId: UUID;
  signalId?: UUID;
  analysisRunId?: UUID;
  decisionType?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResult<JournalEntry[]>> {
  return apiGet<JournalEntry[]>("/journal-entries", {
    optional: true,
    query: {
      workspaceId: params.workspaceId,
      signalId: params.signalId,
      analysisRunId: params.analysisRunId,
      decisionType: params.decisionType,
      status: params.status,
      limit: params.limit || 100,
      offset: params.offset || 0,
    },
  });
}

export function createJournalEntry(payload: JournalEntryCreateRequest): Promise<ApiResult<JournalEntry>> {
  return apiPost<JournalEntry>("/journal-entries", payload, { optional: true });
}

export function getJournalEntry(entryId: UUID): Promise<ApiResult<JournalEntry>> {
  return apiGet<JournalEntry>(`/journal-entries/${entryId}`, { optional: true });
}

export function updateJournalEntry(
  entryId: UUID,
  payload: JournalEntryUpdateRequest,
): Promise<ApiResult<JournalEntry>> {
  return apiPatch<JournalEntry>(`/journal-entries/${entryId}`, payload, { optional: true });
}

export function archiveJournalEntry(entryId: UUID): Promise<ApiResult<JournalEntry>> {
  return apiPost<JournalEntry>(`/journal-entries/${entryId}/archive`, undefined, { optional: true });
}

export function reviewJournalEntry(
  entryId: UUID,
  payload: JournalReviewCreateRequest,
): Promise<ApiResult<JournalEntryReview>> {
  return apiPost<JournalEntryReview>(`/journal-entries/${entryId}/review`, payload, { optional: true });
}

export function listJournalReviews(entryId: UUID): Promise<ApiResult<JournalEntryReview[]>> {
  return apiGet<JournalEntryReview[]>(`/journal-entries/${entryId}/reviews`, { optional: true });
}

export async function getJournalData(params: Record<string, string | undefined>): Promise<JournalData> {
  const env = getPublicEnv();
  const filters = parseJournalFilters(params);
  const failures: JournalFailure[] = [];
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
      analysisRuns: [],
      entryContexts: {},
      filters,
      entries: [],
      unfilteredEntryCount: 0,
      selectedEntry: null,
      outcomes: [],
      failures,
      lastLoadedAt: new Date().toISOString(),
    };
  }

  const resolvedFilters = { ...filters, workspaceId: workspace.id };
  const [entriesResult, linkedOutcomesResult, analysisRunsResult] = await Promise.all([
    listJournalEntries({
      workspaceId: workspace.id,
      signalId: resolvedFilters.signalId,
      analysisRunId: resolvedFilters.analysisRunId,
      decisionType: resolvedFilters.decisionType,
      status: resolvedFilters.status,
      limit: 200,
    }),
    resolvedFilters.signalId ? listSignalOutcomes(resolvedFilters.signalId) : Promise.resolve(null),
    listAnalysisRuns(workspace.id, resolvedFilters.symbolId),
  ]);
  const unfilteredEntries = readResult("Journal entries", entriesResult, [], failures);
  const outcomes = linkedOutcomesResult ? readResult("Linked signal outcomes", linkedOutcomesResult, [], failures) : [];
  const analysisRuns = readResult("Analysis runs", analysisRunsResult, [], failures);
  const entryContexts = buildEntryContexts(unfilteredEntries, analysisRuns, symbols);
  const entries = filterEntriesByContext(unfilteredEntries, entryContexts, resolvedFilters);
  const selectedEntry = await loadSelectedEntry(params.entryId, entries, outcomes, failures);

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace,
    workspaces,
    symbols,
    analysisRuns,
    entryContexts,
    filters: resolvedFilters,
    entries,
    unfilteredEntryCount: unfilteredEntries.length,
    selectedEntry,
    outcomes,
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

async function loadSelectedEntry(
  entryId: string | undefined,
  entries: JournalEntry[],
  knownOutcomes: SignalOutcome[],
  failures: JournalFailure[],
): Promise<JournalData["selectedEntry"]> {
  const entry = entryId ? await loadEntry(entryId, failures) : entries[0] || null;
  if (!entry) {
    return null;
  }
  const [reviewsResult, outcomesResult] = await Promise.all([
    listJournalReviews(entry.id),
    entry.signal_id && knownOutcomes.length === 0 ? listSignalOutcomes(entry.signal_id) : Promise.resolve(null),
  ]);
  const reviews = readResult("Journal reviews", reviewsResult, [], failures);
  const outcomes = outcomesResult ? readResult("Entry signal outcomes", outcomesResult, [], failures) : knownOutcomes;
  return { entry, reviews, outcomes };
}

async function loadEntry(entryId: string, failures: JournalFailure[]): Promise<JournalEntry | null> {
  const result = await getJournalEntry(entryId);
  if (result.ok) {
    return result.data;
  }
  failures.push(journalFailure("Journal entry", result.error));
  return null;
}

function parseJournalFilters(params: Record<string, string | undefined>): JournalFilters {
  return {
    workspaceId: params.workspaceId,
    signalId: params.signalId,
    analysisRunId: params.analysisRunId,
    setupContextId: params.setupContextId,
    outcomeId: params.outcomeId,
    symbolId: params.symbolId,
    timeframe: normalizeTextFilter(params.timeframe),
    decisionType: parseDecisionType(params.decisionType),
    status: parseStatus(params.status),
  };
}

function buildEntryContexts(
  entries: JournalEntry[],
  analysisRuns: JournalData["analysisRuns"],
  symbols: JournalData["symbols"],
): Record<string, JournalEntryContext> {
  const runsById = new Map(analysisRuns.map((run) => [run.id, run]));
  const symbolsById = new Map(symbols.map((symbol) => [symbol.id, symbol]));
  return Object.fromEntries(
    entries.map((entry) => {
      const run = entry.analysis_run_id ? runsById.get(entry.analysis_run_id) || null : null;
      const symbol = run ? symbolsById.get(run.symbol_id) || null : null;
      return [
        entry.id,
        {
          symbolId: run?.symbol_id || null,
          symbol: symbol?.symbol || null,
          timeframe: run?.timeframe || null,
          analysisRunId: run?.id || entry.analysis_run_id || null,
        },
      ];
    }),
  );
}

function filterEntriesByContext(
  entries: JournalEntry[],
  contexts: Record<string, JournalEntryContext>,
  filters: JournalFilters,
): JournalEntry[] {
  return entries.filter((entry) => {
    const context = contexts[entry.id];
    const symbolMatches = !filters.symbolId || context?.symbolId === filters.symbolId;
    const timeframeMatches = !filters.timeframe || context?.timeframe === filters.timeframe;
    return symbolMatches && timeframeMatches;
  });
}

function normalizeTextFilter(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized || undefined;
}

function parseDecisionType(value: string | undefined): JournalDecisionType | undefined {
  const allowed: JournalDecisionType[] = [
    "observed",
    "ignored",
    "reviewed",
    "paper_followed",
    "external_action_taken",
    "no_action",
    "uncertain",
  ];
  return allowed.find((candidate) => candidate === value);
}

function parseStatus(value: string | undefined): JournalStatus | undefined {
  const allowed: JournalStatus[] = ["draft", "saved", "archived"];
  return allowed.find((candidate) => candidate === value);
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: JournalFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(journalFailure(label, result.error));
  return fallback;
}
