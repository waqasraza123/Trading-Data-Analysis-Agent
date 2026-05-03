import { apiGet, apiPost } from "./client";
import type { ApiResult, JournalEntry, JournalEntryCreateRequest, UUID } from "./types";

export function listJournalEntries(params: {
  workspaceId: UUID;
  signalId?: UUID;
  analysisRunId?: UUID;
}): Promise<ApiResult<JournalEntry[]>> {
  return apiGet<JournalEntry[]>("/journal-entries", {
    optional: true,
    query: {
      workspaceId: params.workspaceId,
      signalId: params.signalId,
      analysisRunId: params.analysisRunId,
      limit: 10,
    },
  });
}

export function createJournalEntry(payload: JournalEntryCreateRequest): Promise<ApiResult<JournalEntry>> {
  return apiPost<JournalEntry>("/journal-entries", payload, { optional: true });
}
