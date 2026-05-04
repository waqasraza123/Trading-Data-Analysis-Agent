import { getPublicEnv } from "@/config/env";
import { getWorkspaceBrief } from "./brief";
import { listNotificationEvents } from "./notifications";
import { getProviderHealthSummary, listProviderHealthSnapshots } from "./providerHealth";
import { getQualityScoreboardData } from "./quality";
import { getScannerData } from "./scanner";
import { getSignalTriageBoard } from "./triage";
import { listJournalEntries } from "./journal";
import { composeCommandCenter } from "@/lib/command-center/composeCommandCenter";
import type { CommandCenterData, CommandCenterFailure } from "@/lib/command-center/types";
import type { ProviderHealthSnapshot, ProviderHealthSummary } from "@/lib/provider-health/types";
import type { ApiFailure, ApiResult, JournalEntry, UUID } from "./types";

export async function getCommandCenterData(params: {
  workspaceId?: string;
  preferenceProfileId?: string;
  workflowRunId?: string;
}): Promise<CommandCenterData> {
  const env = getPublicEnv();
  const [brief, triage, scanner] = await Promise.all([
    getWorkspaceBrief(params),
    getSignalTriageBoard(params),
    getScannerData(params),
  ]);
  const workspace = triage.workspace || scanner.workspace || null;
  const { recentJournalEntries, journalEntriesBySignalId, journalFailures, providerHealthSummary, providerHealthSnapshots, providerHealthFailures, notificationUnreadCount, notificationReviewCount, notificationFailures, qualityWarnings, qualityFailures } = workspace
    ? await fetchCommandCenterWorkspaceContext(workspace.id, triage.allCandidates.slice(0, 10).map((candidate) => candidate.signal.signal.id))
    : {
        recentJournalEntries: [],
        journalEntriesBySignalId: new Map<UUID, JournalEntry[]>(),
        journalFailures: [],
        providerHealthSummary: null,
        providerHealthSnapshots: [],
        providerHealthFailures: [],
        notificationUnreadCount: 0,
        notificationReviewCount: 0,
        notificationFailures: [],
        qualityWarnings: [],
        qualityFailures: [],
      };

  return composeCommandCenter({
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: params.workspaceId || null,
    workspace,
    selectedPreferenceProfile: triage.selectedPreferenceProfile,
    providerHealthSummary,
    providerHealthSnapshots,
    generatedAt: new Date().toISOString(),
    brief,
    triage,
    scanner,
    recentJournalEntries,
    journalEntriesBySignalId,
    journalFailures,
    providerHealthFailures,
    notificationUnreadCount,
    notificationReviewCount,
    notificationFailures,
    qualityWarnings,
    qualityFailures,
  });
}

async function fetchCommandCenterWorkspaceContext(
  workspaceId: UUID,
  signalIds: UUID[],
): Promise<{
  recentJournalEntries: JournalEntry[];
  journalEntriesBySignalId: Map<UUID, JournalEntry[]>;
  journalFailures: CommandCenterFailure[];
  providerHealthSummary: ProviderHealthSummary | null;
  providerHealthSnapshots: ProviderHealthSnapshot[];
  providerHealthFailures: CommandCenterFailure[];
  notificationUnreadCount: number;
  notificationReviewCount: number;
  notificationFailures: CommandCenterFailure[];
  qualityWarnings: CommandCenterData["qualityWarnings"];
  qualityFailures: CommandCenterFailure[];
}> {
  const [journalContext, providerHealthContext, notificationContext, qualityContext] = await Promise.all([
    fetchJournalContext(workspaceId, signalIds),
    fetchProviderHealthContext(workspaceId),
    fetchNotificationContext(workspaceId),
    fetchQualityContext(workspaceId),
  ]);
  return {
    ...journalContext,
    ...providerHealthContext,
    ...notificationContext,
    ...qualityContext,
  };
}

async function fetchJournalContext(
  workspaceId: UUID,
  signalIds: UUID[],
): Promise<{
  recentJournalEntries: JournalEntry[];
  journalEntriesBySignalId: Map<UUID, JournalEntry[]>;
  journalFailures: CommandCenterFailure[];
}> {
  const failures: CommandCenterFailure[] = [];
  const recentResult = await listJournalEntries({ workspaceId });
  const recentJournalEntries = readJournalResult("Journal entries", recentResult, failures);
  const uniqueSignalIds = Array.from(new Set(signalIds));
  const signalResults = await Promise.all(
    uniqueSignalIds.map(async (signalId) => ({
      signalId,
      result: await listJournalEntries({ workspaceId, signalId }),
    })),
  );
  const journalEntriesBySignalId = new Map<UUID, JournalEntry[]>();
  for (const { signalId, result } of signalResults) {
    journalEntriesBySignalId.set(signalId, readJournalResult(`Journal entries ${signalId}`, result, failures));
  }
  return {
    recentJournalEntries,
    journalEntriesBySignalId,
    journalFailures: failures,
  };
}

async function fetchProviderHealthContext(
  workspaceId: UUID,
): Promise<{
  providerHealthSummary: ProviderHealthSummary | null;
  providerHealthSnapshots: ProviderHealthSnapshot[];
  providerHealthFailures: CommandCenterFailure[];
}> {
  const failures: CommandCenterFailure[] = [];
  const [summaryResult, snapshotsResult] = await Promise.all([
    getProviderHealthSummary(workspaceId),
    listProviderHealthSnapshots({ workspaceId }),
  ]);
  const providerHealthSummary = readOptionalResult("Provider health summary", summaryResult, failures);
  const providerHealthSnapshots = readOptionalList("Provider health snapshots", snapshotsResult, failures);
  return {
    providerHealthSummary,
    providerHealthSnapshots,
    providerHealthFailures: failures,
  };
}

async function fetchNotificationContext(
  workspaceId: UUID,
): Promise<{
  notificationUnreadCount: number;
  notificationReviewCount: number;
  notificationFailures: CommandCenterFailure[];
}> {
  const failures: CommandCenterFailure[] = [];
  const [unreadResult, reviewResult] = await Promise.all([
    listNotificationEvents({ workspaceId, inboxStatus: "unread", limit: 500 }),
    listNotificationEvents({ workspaceId, inboxStatus: "acknowledged", limit: 500 }),
  ]);
  const unreadEvents = readOptionalList("Unread notification events", unreadResult, failures);
  const reviewEvents = readOptionalList("Acknowledged notification events", reviewResult, failures);
  return {
    notificationUnreadCount: unreadEvents.length,
    notificationReviewCount: reviewEvents.length,
    notificationFailures: failures,
  };
}

async function fetchQualityContext(
  workspaceId: UUID,
): Promise<{
  qualityWarnings: CommandCenterData["qualityWarnings"];
  qualityFailures: CommandCenterFailure[];
}> {
  const data = await getQualityScoreboardData({ workspaceId });
  return {
    qualityWarnings: data.warnings.slice(0, 4),
    qualityFailures: data.failures.map((failure) => ({
      label: `Quality ${failure.label}`,
      status: failure.status,
      message: failure.message,
      missing: failure.missing,
    })),
  };
}

function readJournalResult(
  label: string,
  result: Awaited<ReturnType<typeof listJournalEntries>>,
  failures: CommandCenterFailure[],
): JournalEntry[] {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return [];
}

function readOptionalResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: CommandCenterFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function readOptionalList<T>(
  label: string,
  result: ApiResult<T[]>,
  failures: CommandCenterFailure[],
): T[] {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return [];
}

function toFailure(label: string, result: ApiFailure): CommandCenterFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
