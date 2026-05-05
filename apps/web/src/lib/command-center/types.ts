import type { JournalEntry, UUID, Workspace } from "@/lib/api/types";
import type { DailyWorkflowFailure, DailyWorkflowRun, DailyWorkflowStep } from "@/lib/daily-workflows/types";
import type { PreferenceProfile } from "@/lib/preferences/types";
import type { ProviderHealthSnapshot, ProviderHealthSummary } from "@/lib/provider-health/types";
import type { RuntimeSupervisorHealth } from "@/lib/api/runtimeSupervisor";

export type CommandCenterTone = "neutral" | "good" | "warning" | "danger" | "info";

export type CommandCenterFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type CommandCenterSectionState = "ready" | "empty" | "unavailable";

export type CommandCenterSectionStatus = {
  state: CommandCenterSectionState;
  label: string;
  message: string;
};

export type CommandCenterSummary = {
  changedItemCount: number;
  freshSymbolCount: number;
  staleOrDegradedCount: number;
  missingCandleCount: number;
  providerFailureCount: number;
  dataReadyCount: number;
  unreadNotificationCount: number;
  qualityWarningCount: number;
  runtimeStaleWorkerCount: number;
  runtimePendingRunRequestCount: number;
  reviewFirstCount: number;
  confirmationCount: number;
  avoidCount: number;
  outcomeReadyCount: number;
  dueScanCount: number;
  journalPromptCount: number;
  backendActionCount: number;
};

export type CommandCenterChangedItem = {
  id: string;
  label: string;
  title: string;
  detail: string;
  tone: CommandCenterTone;
  href: string;
};

export type CommandCenterDataReadinessItem = {
  id: string;
  symbol: string;
  timeframe: string | null;
  label: string;
  detail: string;
  tone: CommandCenterTone;
  href: string;
};

export type CommandCenterSetupItem = {
  signalId: UUID;
  symbol: string;
  timeframe: string;
  bias: string;
  confidenceLabel: string;
  setupQualityLabel: string;
  reviewPriorityLabel: string | null;
  mainReason: string;
  detail: string;
  href: string;
};

export type CommandCenterConfirmationItem = {
  id: string;
  symbol: string;
  timeframe: string;
  label: string;
  reason: string;
  href: string;
};

export type CommandCenterAvoidItem = {
  id: string;
  symbol: string;
  timeframe: string | null;
  condition: string;
  reason: string;
  tone: CommandCenterTone;
  href: string;
};

export type CommandCenterOutcomeItem = {
  id: string;
  signalId: UUID;
  symbol: string;
  timeframe: string;
  horizon: string;
  observationLabel: string;
  detail: string;
  href: string;
};

export type CommandCenterScanItem = {
  id: string;
  label: string;
  detail: string;
  status: string;
  tone: CommandCenterTone;
  href: string;
};

export type CommandCenterJournalItem = {
  id: string;
  label: string;
  detail: string;
  href: string;
  entry: JournalEntry | null;
};

export type CommandCenterNextAction = {
  id: string;
  label: string;
  detail: string;
  source: string;
  tone: CommandCenterTone;
  href: string;
};

export type CommandCenterQualityWarning = {
  id: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "danger";
};

export type CommandCenterNavigationItem = {
  id: string;
  label: string;
  detail: string;
  href: string;
  tone: CommandCenterTone;
};

export type CommandCenterData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  selectedPreferenceProfile: PreferenceProfile | null;
  providerHealthSummary: ProviderHealthSummary | null;
  providerHealthSnapshots: ProviderHealthSnapshot[];
  generatedAt: string;
  backendUnavailable: boolean;
  dailyWorkflowRuns: DailyWorkflowRun[];
  selectedDailyWorkflowRun: DailyWorkflowRun | null;
  selectedDailyWorkflowSteps: DailyWorkflowStep[];
  dailyWorkflowDefaultWatchlistId: UUID | null;
  notificationUnreadCount: number;
  notificationReviewCount: number;
  qualityWarnings: CommandCenterQualityWarning[];
  runtimeSupervisorHealth: RuntimeSupervisorHealth | null;
  summary: CommandCenterSummary;
  whatChanged: CommandCenterChangedItem[];
  dataReadiness: CommandCenterDataReadinessItem[];
  reviewFirst: CommandCenterSetupItem[];
  needsConfirmation: CommandCenterConfirmationItem[];
  avoidItems: CommandCenterAvoidItem[];
  outcomeReview: CommandCenterOutcomeItem[];
  scannerStatus: CommandCenterScanItem[];
  journalPrompts: CommandCenterJournalItem[];
  nextActions: CommandCenterNextAction[];
  navigationItems: CommandCenterNavigationItem[];
  sectionStatuses: {
    whatChanged: CommandCenterSectionStatus;
    dataReadiness: CommandCenterSectionStatus;
    reviewFirst: CommandCenterSectionStatus;
    needsConfirmation: CommandCenterSectionStatus;
    avoidItems: CommandCenterSectionStatus;
    outcomeReview: CommandCenterSectionStatus;
    scannerStatus: CommandCenterSectionStatus;
    runtimeWorkers: CommandCenterSectionStatus;
    journalPrompts: CommandCenterSectionStatus;
    nextActions: CommandCenterSectionStatus;
    navigationItems: CommandCenterSectionStatus;
  };
  failures: CommandCenterFailure[];
  dailyWorkflowFailures: DailyWorkflowFailure[];
};
