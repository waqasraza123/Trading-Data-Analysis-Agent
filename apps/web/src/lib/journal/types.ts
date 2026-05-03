import type { ApiError, JournalEntry, JsonRecord, SignalOutcome, UUID, Workspace } from "@/lib/api/types";

export const journalDecisionTypes = [
  "observed",
  "ignored",
  "reviewed",
  "paper_followed",
  "external_action_taken",
  "no_action",
  "uncertain",
] as const;

export const journalUserBiases = ["bullish", "bearish", "neutral", "unclear"] as const;

export const journalStatuses = ["draft", "saved", "archived"] as const;

export type JournalDecisionType = (typeof journalDecisionTypes)[number];
export type JournalUserBias = (typeof journalUserBiases)[number];
export type JournalStatus = (typeof journalStatuses)[number];

export type JournalFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type JournalFilters = {
  workspaceId?: string;
  signalId?: string;
  analysisRunId?: string;
  setupContextId?: string;
  outcomeId?: string;
  decisionType?: JournalDecisionType;
  status?: JournalStatus;
};

export type JournalEntryUpdateRequest = {
  userId?: UUID | null;
  signalId?: UUID | null;
  analysisRunId?: UUID | null;
  setupContextId?: UUID | null;
  chartScreenshotRunId?: UUID | null;
  title?: string;
  status?: JournalStatus;
  decisionType?: JournalDecisionType;
  confidenceBefore?: string | number | null;
  userBias?: JournalUserBias | null;
  userNotes?: string;
  tags?: string[];
  metadata?: JsonRecord;
};

export type JournalReviewCreateRequest = {
  outcomeId?: UUID | null;
  metadata?: JsonRecord;
};

export type JournalEntryReview = {
  id: UUID;
  workspace_id: UUID;
  journal_entry_id: UUID;
  reviewed_at: string;
  outcome_id: UUID | null;
  outcome_label: string | null;
  reflection_label: string;
  reflection_notes: string;
  lessons: string[];
  metadata: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type JournalEntryWithReviews = {
  entry: JournalEntry;
  reviews: JournalEntryReview[];
  outcomes: SignalOutcome[];
};

export type JournalData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: string | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  filters: JournalFilters;
  entries: JournalEntry[];
  selectedEntry: JournalEntryWithReviews | null;
  outcomes: SignalOutcome[];
  failures: JournalFailure[];
  lastLoadedAt: string;
};

export function journalFailure(label: string, error: ApiError): JournalFailure {
  return {
    label,
    status: error.status,
    message: error.missing ? "Endpoint not available yet" : error.message,
    missing: error.missing,
  };
}
