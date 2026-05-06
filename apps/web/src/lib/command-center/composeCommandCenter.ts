import type { JournalEntry, UUID, Workspace } from "@/lib/api/types";
import type { WorkspaceBrief } from "@/lib/brief/types";
import type { PreferenceProfile } from "@/lib/preferences/types";
import { providerHealthReadinessLabel, providerHealthStatusLabel, providerHealthTone } from "@/lib/provider-health/labels";
import type { ProviderHealthSnapshot, ProviderHealthSummary } from "@/lib/provider-health/types";
import type { ScannerData } from "@/lib/scanner/types";
import type { TriageBoardData, TriageCandidate, TriageColumnKey } from "@/lib/triage/types";
import {
  commandCenterHref,
  commandCenterLabel,
  commandCenterText,
  displaySymbol,
  outcomeObservationLabel,
  toneForSeverity,
  toneForState,
} from "./labels";
import type {
  CommandCenterAvoidItem,
  CommandCenterChangedItem,
  CommandCenterConfirmationItem,
  CommandCenterData,
  CommandCenterDataReadinessItem,
  CommandCenterFailure,
  CommandCenterJournalItem,
  CommandCenterNavigationItem,
  CommandCenterNextAction,
  CommandCenterOutcomeItem,
  CommandCenterScanItem,
  CommandCenterSectionStatus,
  CommandCenterSetupItem,
  CommandCenterTone,
} from "./types";

type ComposeCommandCenterInput = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  selectedPreferenceProfile: PreferenceProfile | null;
  providerHealthSummary: ProviderHealthSummary | null;
  providerHealthSnapshots: ProviderHealthSnapshot[];
  providerPollingRequests: CommandCenterData["providerPollingRequests"];
  generatedAt: string;
  brief: WorkspaceBrief;
  triage: TriageBoardData;
  scanner: ScannerData;
  recentJournalEntries: JournalEntry[];
  journalEntriesBySignalId: Map<UUID, JournalEntry[]>;
  journalFailures: CommandCenterFailure[];
  providerHealthFailures: CommandCenterFailure[];
  notificationUnreadCount: number;
  notificationReviewCount: number;
  notificationFailures: CommandCenterFailure[];
  latestProductReadiness: CommandCenterData["latestProductReadiness"];
  readinessFailures: CommandCenterFailure[];
  qualityWarnings: CommandCenterData["qualityWarnings"];
  qualityFailures: CommandCenterFailure[];
  runtimeSupervisorHealth: CommandCenterData["runtimeSupervisorHealth"];
  runtimeSupervisorFailures: CommandCenterFailure[];
  workspaceOverview: CommandCenterData["workspaceOverview"];
  workspaceOverviewFailure: CommandCenterData["workspaceOverviewFailure"];
  dailyRoutineTemplates: CommandCenterData["dailyRoutineTemplates"];
  dailyRoutineRuns: CommandCenterData["dailyRoutineRuns"];
  selectedDailyRoutineRun: CommandCenterData["selectedDailyRoutineRun"];
  selectedDailyRoutineRunSteps: CommandCenterData["selectedDailyRoutineRunSteps"];
  dailyRoutineFailures: CommandCenterData["dailyRoutineFailures"];
};

const reviewColumns: TriageColumnKey[] = ["high_quality_context"];
const confirmationColumns: TriageColumnKey[] = ["needs_confirmation", "conflicted", "stale_data_issue"];
const avoidColumns: TriageColumnKey[] = ["avoid_no_directional_signal", "review_required"];

export function composeCommandCenter(input: ComposeCommandCenterInput): CommandCenterData {
  const workspaceId = input.workspace?.id || null;
  const failures = mergeFailures(
    input.brief.failures,
    input.triage.failures,
    input.scanner.failures,
    input.journalFailures,
    input.providerHealthFailures,
    input.notificationFailures,
    input.readinessFailures,
    input.qualityFailures,
    input.runtimeSupervisorFailures,
    input.workspaceOverviewFailure ? [input.workspaceOverviewFailure] : [],
    input.dailyRoutineFailures,
  );
  const dailyWorkflowFailures = input.scanner.dailyWorkflowFailures;
  const dailyRoutineFailures = input.dailyRoutineFailures;
  const whatChanged = buildWhatChanged(input.brief, input.triage, workspaceId);
  const dataReadiness = buildDataReadiness(input.brief, input.providerHealthSnapshots, workspaceId);
  const reviewFirst = buildReviewFirst(input.triage, workspaceId);
  const needsConfirmation = buildNeedsConfirmation(input.triage, workspaceId);
  const avoidItems = buildAvoidItems(input.brief, input.triage, workspaceId);
  const outcomeReview = buildOutcomeReview(input.brief, workspaceId);
  const scannerStatus = buildScannerStatus(input.scanner, workspaceId);
  const journalPrompts = buildJournalPrompts(input.triage, input.recentJournalEntries, input.journalEntriesBySignalId, workspaceId);
  const nextActions = buildNextActions(
    input.brief,
    input.triage,
    input.scanner,
    input.providerHealthSummary,
    input.providerHealthSnapshots,
    journalPrompts,
    input.notificationUnreadCount,
    input.qualityWarnings,
    workspaceId,
  );
  const navigationItems = buildNavigationItems(workspaceId);
  const backendUnavailable = input.brief.backendUnavailable || failures.some((failure) => failure.status === 0);

  return {
    appName: input.appName,
    apiBaseUrl: input.apiBaseUrl,
    requestedWorkspaceId: input.requestedWorkspaceId,
    workspace: input.workspace,
    selectedPreferenceProfile: input.selectedPreferenceProfile,
    providerHealthSummary: input.providerHealthSummary,
    providerHealthSnapshots: input.providerHealthSnapshots,
    providerPollingRequests: input.providerPollingRequests,
    generatedAt: input.generatedAt,
    backendUnavailable,
    dailyWorkflowRuns: input.scanner.dailyWorkflowRuns,
    selectedDailyWorkflowRun: input.scanner.selectedDailyWorkflowRun,
    selectedDailyWorkflowSteps: input.scanner.selectedDailyWorkflowSteps,
    dailyWorkflowDefaultWatchlistId: input.scanner.watchlists[0]?.watchlist.id || null,
    dailyRoutineTemplates: input.dailyRoutineTemplates,
    dailyRoutineRuns: input.dailyRoutineRuns,
    selectedDailyRoutineRun: input.selectedDailyRoutineRun,
    selectedDailyRoutineRunSteps: input.selectedDailyRoutineRunSteps,
    notificationUnreadCount: input.notificationUnreadCount,
    notificationReviewCount: input.notificationReviewCount,
    latestProductReadiness: input.latestProductReadiness,
    qualityWarnings: input.qualityWarnings,
    runtimeSupervisorHealth: input.runtimeSupervisorHealth,
    workspaceOverview: input.workspaceOverview,
    workspaceOverviewFailure: input.workspaceOverviewFailure,
    summary: {
      changedItemCount: whatChanged.length,
      freshSymbolCount: input.providerHealthSummary?.fresh_count ?? input.brief.summary.freshSymbols,
      staleOrDegradedCount: providerStaleOrDegradedCount(input.providerHealthSummary) ?? input.brief.summary.staleOrDegradedSymbols,
      missingCandleCount: input.providerHealthSummary?.missing_candle_count ?? 0,
      providerFailureCount: input.providerHealthSummary?.provider_failure_count ?? 0,
      dataReadyCount: input.providerHealthSummary?.ready_for_deterministic_analysis_count ?? 0,
      unreadNotificationCount: input.notificationUnreadCount,
      qualityWarningCount: input.qualityWarnings.length,
      runtimeStaleWorkerCount: input.runtimeSupervisorHealth?.stale_instance_count ?? 0,
      runtimePendingRunRequestCount: input.runtimeSupervisorHealth?.pending_run_request_count ?? 0,
      reviewFirstCount: reviewFirst.length,
      confirmationCount: needsConfirmation.length,
      avoidCount: avoidItems.length,
      outcomeReadyCount: outcomeReview.length,
      dueScanCount: input.scanner.dueScanConfigs.length,
      journalPromptCount: journalPrompts.length,
      backendActionCount: nextActions.length,
    },
    whatChanged,
    dataReadiness,
    reviewFirst,
    needsConfirmation,
    avoidItems,
    outcomeReview,
    scannerStatus,
    journalPrompts,
    nextActions,
    navigationItems,
    sectionStatuses: {
      whatChanged: sectionStatus("What changed", whatChanged.length, failures, ["Signal digests", "Signal outcomes", "Operator reviews"]),
      dataReadiness: sectionStatus("Data readiness", dataReadiness.length, failures, ["Market memory", "Data sources"]),
      reviewFirst: sectionStatus("Review first", reviewFirst.length, failures, ["Signals", "Setup context", "Decision readiness"]),
      needsConfirmation: sectionStatus("Needs confirmation", needsConfirmation.length, failures, ["Signals", "Decision readiness"]),
      avoidItems: sectionStatus("Avoid conditions", avoidItems.length, failures, ["Market memory", "Setup context"]),
      outcomeReview: sectionStatus("Outcome review", outcomeReview.length, failures, ["Signal outcomes"]),
      scannerStatus: sectionStatus("Scanner status", scannerStatus.length, failures, ["Scheduled scan configs"]),
      runtimeWorkers: runtimeWorkerSectionStatus(input.runtimeSupervisorHealth, failures),
      journalPrompts: sectionStatus("Journal prompt", journalPrompts.length, failures, ["Journal entries"]),
      nextActions: sectionStatus("Next backend-safe actions", nextActions.length, failures, ["Backend action items", "Scheduled scans"]),
      navigationItems: sectionStatus("Daily workflow links", navigationItems.length, failures, []),
    },
    failures,
    dailyWorkflowFailures,
    dailyRoutineFailures,
  };
}

function buildWhatChanged(
  brief: WorkspaceBrief,
  triage: TriageBoardData,
  workspaceId: UUID | null,
): CommandCenterChangedItem[] {
  const digestItems: CommandCenterChangedItem[] = brief.digestSummaries.slice(0, 3).map((item) => ({
    id: `digest:${item.id}`,
    label: "Digest summary",
    title: commandCenterText(item.title, "Digest update"),
    detail: commandCenterText(item.summary, "Digest context available"),
    tone: toneForState(item.priority),
    href: item.signalId ? `/signals/${item.signalId}` : commandCenterHref("/brief", workspaceId),
  }));
  const signalItems: CommandCenterChangedItem[] = triage.allCandidates.slice(0, 3).map((candidate) => ({
    id: `signal:${candidate.id}`,
    label: "Signal context",
    title: `${candidateSymbol(candidate)} ${candidate.signal.signal.timeframe}`,
    detail: commandCenterText(candidate.classification.mainReason.label, "Review recommended"),
    tone: candidate.classification.mainReason.tone,
    href: `/signals/${candidate.signal.signal.id}`,
  }));
  const outcomeItems: CommandCenterChangedItem[] = brief.outcomeUpdates.slice(0, 2).map((outcome) => ({
    id: `outcome:${outcome.id}`,
    label: "Outcome ready",
    title: `${outcome.symbol} ${outcome.timeframe}`,
    detail: commandCenterText(outcome.observationLabel, "Outcome ready"),
    tone: "info",
    href: `/signals/${outcome.signalId}`,
  }));
  const dataItems: CommandCenterChangedItem[] = brief.dataQualityIssues.slice(0, 2).map((issue) => ({
    id: `data:${issue.id}`,
    label: "Data state",
    title: `${issue.symbol}${issue.timeframe ? ` ${issue.timeframe}` : ""}`,
    detail: commandCenterText(issue.detail, "Review data freshness"),
    tone: toneForSeverity(issue.severity),
    href: commandCenterHref("/data/onboarding", workspaceId),
  }));
  const reviewItems: CommandCenterChangedItem[] = brief.reviewNeeded.slice(0, 2).map((item) => ({
    id: `review:${item.id}`,
    label: "Review required",
    title: commandCenterText(item.label, "Review required"),
    detail: commandCenterText(item.reason, "Review queue item"),
    tone: toneForSeverity(item.priority),
    href: item.signalId ? `/signals/${item.signalId}` : commandCenterHref("/triage?onlyReviewRequired=1", workspaceId),
  }));
  return uniqueBy([...digestItems, ...signalItems, ...outcomeItems, ...dataItems, ...reviewItems], (item) => item.id).slice(0, 9);
}

function buildDataReadiness(
  brief: WorkspaceBrief,
  providerHealthSnapshots: ProviderHealthSnapshot[],
  workspaceId: UUID | null,
): CommandCenterDataReadinessItem[] {
  const providerItems = providerHealthSnapshots.slice(0, 10).map((snapshot) => ({
    id: `provider:${snapshot.id}`,
    symbol: providerSnapshotSymbol(snapshot),
    timeframe: snapshot.timeframe,
    label: providerHealthReadinessLabel(snapshot),
    detail: providerSnapshotDetail(snapshot),
    tone: providerHealthTone(snapshot.status),
    href: commandCenterHref("/data/onboarding", workspaceId),
  }));
  const focusItems = brief.marketFocus.slice(0, 8).map((item) => ({
    id: `focus:${item.id}`,
    symbol: item.symbol,
    timeframe: item.timeframe,
    label: item.freshnessLabel === "fresh" ? "Fresh symbol" : "Data stale",
    detail: commandCenterText(`${commandCenterLabel(item.dataQualityLabel)} quality. ${item.topWarning}`),
    tone: toneForState(item.freshnessLabel === "fresh" ? item.dataQualityLabel : item.freshnessLabel),
    href: `/symbols/${item.symbolId}${workspaceId ? `?workspaceId=${workspaceId}` : ""}`,
  }));
  const issueItems = brief.dataQualityIssues.slice(0, 6).map((item) => ({
    id: `issue:${item.id}`,
    symbol: item.symbol,
    timeframe: item.timeframe,
    label: commandCenterText(item.label, "Data quality issue"),
    detail: commandCenterText(item.detail, "Review data freshness"),
    tone: toneForSeverity(item.severity),
    href: commandCenterHref("/data/onboarding", workspaceId),
  }));
  return uniqueBy([...providerItems, ...issueItems, ...focusItems], (item) => `${item.symbol}:${item.timeframe}:${item.label}`).slice(0, 10);
}

function buildReviewFirst(triage: TriageBoardData, workspaceId: UUID | null): CommandCenterSetupItem[] {
  const preferred = triage.allCandidates.filter((candidate) => reviewColumns.includes(candidate.classification.column));
  const fallback = triage.allCandidates.filter((candidate) => {
    const confidence = candidate.signal.signal.confidence_label.toLowerCase();
    return ["high", "strong"].includes(confidence) && candidate.memory?.freshness_label === "fresh";
  });
  return uniqueBy([...preferred, ...fallback], (candidate) => candidate.id)
    .slice(0, 6)
    .map((candidate) => setupItem(candidate, workspaceId));
}

function buildNeedsConfirmation(triage: TriageBoardData, workspaceId: UUID | null): CommandCenterConfirmationItem[] {
  return triage.allCandidates
    .filter((candidate) => confirmationColumns.includes(candidate.classification.column))
    .slice(0, 8)
    .map((candidate) => ({
      id: candidate.id,
      symbol: candidateSymbol(candidate),
      timeframe: candidate.signal.signal.timeframe,
      label: commandCenterText(candidate.classification.mainReason.label, "Needs confirmation"),
      reason: commandCenterText(candidate.classification.reasons.map((item) => item.label).slice(0, 3).join(", "), "Review context"),
      href: commandCenterHref(`/triage?column=${candidate.classification.column}`, workspaceId),
    }));
}

function buildAvoidItems(
  brief: WorkspaceBrief,
  triage: TriageBoardData,
  workspaceId: UUID | null,
): CommandCenterAvoidItem[] {
  const triageItems = triage.allCandidates
    .filter((candidate) => avoidColumns.includes(candidate.classification.column))
    .slice(0, 8)
    .map((candidate) => {
      const tone: CommandCenterTone = candidate.classification.column === "review_required" ? "danger" : "warning";
      return {
        id: `triage:${candidate.id}`,
        symbol: candidateSymbol(candidate),
        timeframe: candidate.signal.signal.timeframe,
        condition: commandCenterText(candidate.classification.mainReason.label, "Avoid condition"),
        reason: commandCenterText(candidate.signal.signal.no_signal_reason || candidate.classification.mainReason.label, "Review context"),
        tone,
        href: `/signals/${candidate.signal.signal.id}`,
      };
    });
  const briefItems = brief.avoidConditions.slice(0, 8).map((item) => ({
    id: `brief:${item.id}`,
    symbol: item.symbol,
    timeframe: item.timeframe,
    condition: commandCenterText(item.condition, "Avoid condition"),
    reason: commandCenterText(item.reason, "Review context"),
    tone: toneForSeverity(item.severity),
    href: item.signalId ? `/signals/${item.signalId}` : commandCenterHref("/triage?column=avoid_no_directional_signal", workspaceId),
  }));
  return uniqueBy([...triageItems, ...briefItems], (item) => `${item.symbol}:${item.timeframe}:${item.condition}:${item.reason}`).slice(0, 10);
}

function buildOutcomeReview(brief: WorkspaceBrief, workspaceId: UUID | null): CommandCenterOutcomeItem[] {
  return brief.outcomeUpdates.slice(0, 8).map((outcome) => ({
    id: outcome.id,
    signalId: outcome.signalId,
    symbol: outcome.symbol,
    timeframe: outcome.timeframe,
    horizon: outcome.horizon,
    observationLabel: commandCenterText(outcome.observationLabel, "Outcome ready"),
    detail: commandCenterText(outcome.safeSummary, outcomeObservationLabel(null, false)),
    href: `/signals/${outcome.signalId}${workspaceId ? `?workspaceId=${workspaceId}` : ""}`,
  }));
}

function buildScannerStatus(scanner: ScannerData, workspaceId: UUID | null): CommandCenterScanItem[] {
  const dueItems = scanner.dueScanConfigs.slice(0, 6).map((config) => ({
    id: `due:${config.id}`,
    label: "Due scan",
    detail: commandCenterText(`${config.name} ${config.timeframe || "configured timeframe"}`),
    status: "due",
    tone: "warning" as const,
    href: commandCenterHref("/scanner", workspaceId),
  }));
  const configItems = scanner.scanConfigs.slice(0, 4).map((config) => ({
    id: `config:${config.id}`,
    label: "Scheduled scan",
    detail: commandCenterText(`${config.name} ${config.scan_mode}`),
    status: config.status,
    tone: toneForState(config.status),
    href: commandCenterHref("/scanner", workspaceId),
  }));
  const runItems = scanner.recentRuns.slice(0, 3).map((run) => ({
    id: `run:${run.id}`,
    label: "Latest scan run",
    detail: commandCenterText(`${run.analysis_run_count} analysis runs, ${run.failed_count} failed, ${run.skipped_count} skipped`),
    status: run.status,
    tone: run.failed_count > 0 ? "danger" : toneForState(run.status),
    href: commandCenterHref(`/scanner?runId=${run.id}`, workspaceId),
  }));
  return [...dueItems, ...runItems, ...configItems].slice(0, 10);
}

function buildJournalPrompts(
  triage: TriageBoardData,
  recentJournalEntries: JournalEntry[],
  journalEntriesBySignalId: Map<UUID, JournalEntry[]>,
  workspaceId: UUID | null,
): CommandCenterJournalItem[] {
  const missingJournal = triage.allCandidates
    .filter((candidate) => candidate.reviews.length > 0 || candidate.outcomes.length > 0 || candidate.actionItems.length > 0)
    .filter((candidate) => (journalEntriesBySignalId.get(candidate.signal.signal.id) || []).length === 0)
    .slice(0, 5)
    .map((candidate) => ({
      id: `prompt:${candidate.id}`,
      label: "Journal prompt",
      detail: `${candidateSymbol(candidate)} ${candidate.signal.signal.timeframe} reviewed without a journal note.`,
      href: `/signals/${candidate.signal.signal.id}`,
      entry: null,
    }));
  const recentEntries = recentJournalEntries.slice(0, 4).map((entry) => ({
    id: `entry:${entry.id}`,
    label: commandCenterText(entry.title, "Recent journal note"),
    detail: commandCenterText(entry.user_notes, "Recent journal note"),
    href: entry.signal_id ? `/signals/${entry.signal_id}` : commandCenterHref("/triage", workspaceId),
    entry,
  }));
  return [...missingJournal, ...recentEntries].slice(0, 8);
}

function buildNextActions(
  brief: WorkspaceBrief,
  triage: TriageBoardData,
  scanner: ScannerData,
  providerHealthSummary: ProviderHealthSummary | null,
  providerHealthSnapshots: ProviderHealthSnapshot[],
  journalPrompts: CommandCenterJournalItem[],
  notificationUnreadCount: number,
  qualityWarnings: CommandCenterData["qualityWarnings"],
  workspaceId: UUID | null,
): CommandCenterNextAction[] {
  const actions: CommandCenterNextAction[] = [];
  if (scanner.presets.length > 0) {
    actions.push(action("open-scanner-presets", "Open scanner presets", `${scanner.presets.length} preset templates are available for explicit scan setup.`, "Scanner", "info", commandCenterHref("/scanner", workspaceId)));
  }
  if (scanner.dueScanConfigs.length > 0) {
    actions.push(action("run-deterministic-scan", "Run deterministic scan", `${scanner.dueScanConfigs.length} scan configs are due.`, "Scanner", "warning", commandCenterHref("/scanner", workspaceId)));
  }
  if (notificationUnreadCount > 0) {
    actions.push(action("review-notification-events", "Review notification events", `${notificationUnreadCount} unread in-app intelligence events are waiting.`, "Notifications", "info", commandCenterHref("/notifications", workspaceId)));
  }
  if (qualityWarnings.length > 0) {
    actions.push(action("review-quality-warnings", "Review quality warnings", qualityWarnings[0].detail, "Quality", qualityWarnings.some((item) => item.severity === "danger") ? "danger" : "warning", commandCenterHref("/quality", workspaceId)));
  }
  const needsProviderRecovery =
    (providerHealthSummary?.missing_candle_count || 0) > 0 ||
    providerHealthSnapshots.some((snapshot) => snapshot.status === "stale" || snapshot.missing_candle_count > 0);
  if (brief.dataQualityIssues.length > 0 || needsProviderRecovery) {
    actions.push(action("review-data-freshness", "Review data freshness", `${brief.dataQualityIssues.length} data issues need review.`, "Data readiness", "warning", commandCenterHref("/data/onboarding", workspaceId)));
  }
  if (needsProviderRecovery) {
    actions.push(action("prepare-gap-recovery", "Prepare gap recovery", "Use data onboarding for candle gap recovery planning.", "Data readiness", "info", commandCenterHref("/data/onboarding", workspaceId)));
  }
  const firstSetup = triage.allCandidates[0] || null;
  if (firstSetup) {
    actions.push(action("inspect-setup-context", "Inspect setup context", `${candidateSymbol(firstSetup)} ${firstSetup.signal.signal.timeframe}`, "Setup context", "info", `/signals/${firstSetup.signal.signal.id}`));
    actions.push(action("inspect-audit-timeline", "Inspect audit timeline", `${candidateSymbol(firstSetup)} stored artifact timeline.`, "Audit timeline", "neutral", `/signals/${firstSetup.signal.signal.id}`));
  }
  if (brief.outcomeUpdates.length > 0) {
    actions.push(action("evaluate-outcome-after-horizon", "Evaluate outcome after horizon", `${brief.outcomeUpdates.length} outcome updates available.`, "Outcome review", "info", `/signals/${brief.outcomeUpdates[0].signalId}`));
  }
  if (journalPrompts.length > 0) {
    actions.push(action("review-journal", "Review journal", `${journalPrompts.length} journal prompts or notes available.`, "Journal", "neutral", journalPrompts[0].href));
  }
  return uniqueBy(actions, (item) => item.id).slice(0, 8);
}

function buildNavigationItems(workspaceId: UUID | null): CommandCenterNavigationItem[] {
  return [
    { id: "brief", label: "Brief", detail: "Read what changed first.", href: commandCenterHref("/brief", workspaceId), tone: "info" },
    { id: "triage", label: "Triage", detail: "Sort signals by review state.", href: commandCenterHref("/triage", workspaceId), tone: "warning" },
    { id: "scanner", label: "Scanner", detail: "Run or inspect deterministic scans.", href: commandCenterHref("/scanner", workspaceId), tone: "good" },
    { id: "notifications", label: "Notifications", detail: "Review in-app intelligence events.", href: commandCenterHref("/notifications", workspaceId), tone: "info" },
    { id: "data", label: "Data", detail: "Review freshness and recovery setup.", href: commandCenterHref("/data/onboarding", workspaceId), tone: "neutral" },
    { id: "quality", label: "Quality", detail: "Review signal quality and drift.", href: commandCenterHref("/quality", workspaceId), tone: "info" },
    { id: "preferences", label: "Preferences", detail: "Set review workflow filters.", href: commandCenterHref("/preferences/strategy", workspaceId), tone: "neutral" },
    { id: "review", label: "Review", detail: "Inspect observed outcomes.", href: commandCenterHref("/review/outcomes", workspaceId), tone: "info" },
    { id: "journal", label: "Journal", detail: "Open journal reflection.", href: commandCenterHref("/journal", workspaceId), tone: "neutral" },
  ];
}

function setupItem(candidate: TriageCandidate, workspaceId: UUID | null): CommandCenterSetupItem {
  const signal = candidate.signal.signal;
  return {
    signalId: signal.id,
    symbol: candidateSymbol(candidate),
    timeframe: signal.timeframe,
    bias: commandCenterLabel(candidate.setupContext?.directional_bias || signal.bias),
    confidenceLabel: commandCenterLabel(signal.confidence_label),
    setupQualityLabel: commandCenterLabel(candidate.setupContext?.setup_quality_label || "Not available"),
    reviewPriorityLabel: reviewPriorityLabel(candidate),
    freshnessLabel: commandCenterLabel(candidate.memory?.freshness_label || "Not available"),
    mainReason: commandCenterText(candidate.classification.mainReason.label, "Review first"),
    detail: commandCenterText(signal.summary || candidate.setupContext?.summary, "Setup context available"),
    href: `/signals/${signal.id}${workspaceId ? `?workspaceId=${workspaceId}` : ""}`,
  };
}

function providerStaleOrDegradedCount(summary: ProviderHealthSummary | null): number | null {
  if (!summary) {
    return null;
  }
  return summary.stale_count + summary.degraded_count + summary.failing_count + summary.unavailable_count;
}

function providerSnapshotSymbol(snapshot: ProviderHealthSnapshot): string {
  return (
    metadataString(snapshot.metadata_json.symbol) ||
    metadataString(snapshot.metadata_json.provider_symbol) ||
    metadataString(snapshot.metadata_json.symbol_name) ||
    snapshot.symbol_id ||
    snapshot.provider ||
    snapshot.source_id
  );
}

function providerSnapshotDetail(snapshot: ProviderHealthSnapshot): string {
  const parts = [
    providerHealthStatusLabel(snapshot.status),
    snapshot.latest_final_candle_time ? `latest final candle ${snapshot.latest_final_candle_time}` : "latest final candle unavailable",
    snapshot.missing_candle_count > 0 ? `${snapshot.missing_candle_count} missing candles` : "no missing candles",
    snapshot.consecutive_failure_count > 0 ? `${snapshot.consecutive_failure_count} recent polling failures` : null,
  ];
  return commandCenterText(parts.filter(Boolean).join(". "), "Review data freshness");
}

function reviewPriorityLabel(candidate: TriageCandidate): string | null {
  const score = candidate.priorityScore;
  if (!score) {
    return null;
  }
  const value = Number(score.priority_score);
  const scoreLabel = Number.isFinite(value) ? `${Math.round(value * 100)}%` : commandCenterLabel(score.priority_label);
  return `Review priority ${scoreLabel}`;
}

function metadataString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function candidateSymbol(candidate: TriageCandidate): string {
  return displaySymbol(candidate.symbol?.symbol, candidate.signal.signal.symbol_id);
}

function action(
  id: string,
  label: string,
  detail: string,
  source: string,
  tone: CommandCenterNextAction["tone"],
  href: string,
): CommandCenterNextAction {
  return {
    id,
    label,
    detail: commandCenterText(detail),
    source,
    tone,
    href,
  };
}

function sectionStatus(
  label: string,
  itemCount: number,
  failures: CommandCenterFailure[],
  relevantLabels: string[],
): CommandCenterSectionStatus {
  const unavailable = failures.some((failure) =>
    !failure.missing && relevantLabels.some((relevantLabel) => failure.label.includes(relevantLabel)),
  );
  if (unavailable) {
    return {
      state: "unavailable",
      label: `${label} unavailable`,
      message: "Backend data for this section is unavailable.",
    };
  }
  if (itemCount > 0) {
    return {
      state: "ready",
      label,
      message: `${itemCount} items available.`,
    };
  }
  return {
    state: "empty",
    label: `${label} clear`,
    message: "No items available for this section.",
  };
}

function runtimeWorkerSectionStatus(
  health: CommandCenterData["runtimeSupervisorHealth"],
  failures: CommandCenterFailure[],
): CommandCenterSectionStatus {
  const unavailable = failures.some((failure) => failure.label.includes("Runtime supervisor") && !failure.missing);
  if (unavailable) {
    return {
      state: "unavailable",
      label: "Worker runtime unavailable",
      message: "Runtime supervisor status is unavailable.",
    };
  }
  if (!health || health.worker_count === 0) {
    return {
      state: "empty",
      label: "Workers not seeded",
      message: "Runtime worker definitions are not available.",
    };
  }
  return {
    state: health.status === "healthy" ? "ready" : "unavailable",
    label: `Runtime ${commandCenterLabel(health.status)}`,
    message: `${health.running_instance_count} running workers, ${health.stale_instance_count} stale workers.`,
  };
}

function mergeFailures(
  ...groups: Array<Array<{ label: string; status: number; message: string; missing: boolean }>>
): CommandCenterFailure[] {
  return uniqueBy(groups.flat(), (failure) => `${failure.label}:${failure.status}:${failure.message}`);
}

function uniqueBy<T>(items: T[], keyForItem: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = keyForItem(item);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}
