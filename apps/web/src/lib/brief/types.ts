import type { UUID } from "@/lib/api/types";

export type BriefSectionState = "ready" | "empty" | "unavailable";

export type BriefSectionStatus = {
  state: BriefSectionState;
  label: string;
  message: string;
};

export type BriefFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type BriefSummary = {
  totalSymbolsReviewed: number;
  freshSymbols: number;
  staleOrDegradedSymbols: number;
  activeSetupCount: number;
  reviewRecommendedCount: number;
  recentOutcomeUpdateCount: number;
  pendingBackendActionCount: number;
};

export type BriefMarketFocusItem = {
  id: string;
  symbolId: UUID;
  symbol: string;
  displayName: string;
  timeframe: string;
  latestBias: string;
  confidenceLabel: string;
  freshnessLabel: string;
  dataQualityLabel: string;
  marketRegimeLabel: string;
  marketSessionLabel: string;
  setupQualityLabel: string;
  topWarning: string;
  signalId: UUID | null;
};

export type BriefActiveSetupItem = {
  signalId: UUID;
  symbolId: UUID;
  symbol: string;
  timeframe: string;
  bias: string;
  patternType: string;
  confidenceLabel: string;
  setupQualityLabel: string;
  keyEvidence: string[];
  invalidationContext: string | null;
  waitCondition: string | null;
  reviewLink: string;
};

export type BriefAvoidConditionItem = {
  id: string;
  symbolId: UUID | null;
  symbol: string;
  timeframe: string | null;
  condition: string;
  reason: string;
  severity: string;
  source: string;
  signalId: UUID | null;
};

export type BriefOutcomeUpdateItem = {
  id: string;
  signalId: UUID;
  symbolId: UUID;
  symbol: string;
  timeframe: string;
  horizon: string;
  outcomeLabel: string;
  observationLabel: string;
  safeSummary: string;
};

export type BriefPendingActionItem = {
  id: UUID;
  actionType: string;
  status: string;
  dueTime: string | null;
  source: string;
  safeLabel: string;
};

export type BriefDataQualityIssue = {
  id: string;
  symbolId: UUID | null;
  symbol: string;
  timeframe: string | null;
  label: string;
  detail: string;
  severity: string;
  source: string;
};

export type BriefWatchNextItem = {
  id: string;
  symbolId: UUID;
  symbol: string;
  timeframe: string;
  observation: string;
  reason: string;
  sourceArtifact: string;
  signalId: UUID | null;
};

export type BriefReviewNeededItem = {
  id: string;
  label: string;
  reason: string;
  priority: string;
  source: string;
  signalId: UUID | null;
};

export type BriefDigestSummary = {
  id: UUID;
  title: string;
  summary: string;
  priority: string;
  itemType: string;
  signalId: UUID | null;
};

export type WorkspaceBrief = {
  appName: string;
  apiBaseUrl: string;
  workspace: {
    id: UUID;
    name: string;
  } | null;
  requestedWorkspaceId: UUID | null;
  generatedAt: string;
  periodStart: string | null;
  periodEnd: string | null;
  timezone: string | null;
  watchlistId: UUID | null;
  sourceLabel: string;
  backendUnavailable: boolean;
  summary: BriefSummary;
  marketFocus: BriefMarketFocusItem[];
  activeSetups: BriefActiveSetupItem[];
  avoidConditions: BriefAvoidConditionItem[];
  outcomeUpdates: BriefOutcomeUpdateItem[];
  pendingActions: BriefPendingActionItem[];
  dataQualityIssues: BriefDataQualityIssue[];
  watchNext: BriefWatchNextItem[];
  reviewNeeded: BriefReviewNeededItem[];
  digestSummaries: BriefDigestSummary[];
  sectionStatuses: {
    workspace: BriefSectionStatus;
    marketFocus: BriefSectionStatus;
    activeSetups: BriefSectionStatus;
    avoidConditions: BriefSectionStatus;
    outcomeUpdates: BriefSectionStatus;
    pendingActions: BriefSectionStatus;
    dataQuality: BriefSectionStatus;
    watchNext: BriefSectionStatus;
    reviewNeeded: BriefSectionStatus;
    digests: BriefSectionStatus;
  };
  failures: BriefFailure[];
};
