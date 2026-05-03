import { apiGet, apiPatch, apiPost } from "./client";
import { getPublicEnv } from "@/config/env";
import {
  journalFailure,
  type JournalData,
  type JournalDecisionType,
  type JournalEntryReview,
  type JournalEntryUpdateRequest,
  type JournalFailure,
  type JournalFilters,
  type JournalReviewCreateRequest,
  type JournalStatus,
} from "@/lib/journal/types";
import { listWorkspaces } from "./market";
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
  const workspacesResult = await listWorkspaces();
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const workspace = workspaces.find((candidate) => candidate.id === filters.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: filters.workspaceId || null,
      workspace: null,
      workspaces,
      filters,
      entries: [],
      selectedEntry: null,
      outcomes: [],
      failures,
      lastLoadedAt: new Date().toISOString(),
    };
  }

  const resolvedFilters = { ...filters, workspaceId: workspace.id };
  const [entriesResult, linkedOutcomesResult] = await Promise.all([
    listJournalEntries({
      workspaceId: workspace.id,
      signalId: resolvedFilters.signalId,
      analysisRunId: resolvedFilters.analysisRunId,
      decisionType: resolvedFilters.decisionType,
      status: resolvedFilters.status,
      limit: 200,
    }),
    resolvedFilters.signalId ? listSignalOutcomes(resolvedFilters.signalId) : Promise.resolve(null),
  ]);
  const entries = readResult("Journal entries", entriesResult, [], failures);
  const outcomes = linkedOutcomesResult ? readResult("Linked signal outcomes", linkedOutcomesResult, [], failures) : [];
  const selectedEntry = await loadSelectedEntry(params.entryId, entries, outcomes, failures);

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace,
    workspaces,
    filters: resolvedFilters,
    entries,
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
    decisionType: parseDecisionType(params.decisionType),
    status: parseStatus(params.status),
  };
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
