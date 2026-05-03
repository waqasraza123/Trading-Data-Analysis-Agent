import { apiGet } from "./client";
import type { ApiResult, JournalEntry, UUID } from "./types";

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
