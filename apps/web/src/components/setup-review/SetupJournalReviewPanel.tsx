import { SetupJournalPanel } from "@/components/setup-detail/SetupJournalPanel";
import type { UUID } from "@/lib/api/types";
import type { SetupReviewModel } from "@/lib/setup-review/types";

type SetupJournalReviewPanelProps = {
  apiBaseUrl: string;
  workspaceId: UUID | null;
  signalId: UUID;
  model: SetupReviewModel;
};

export function SetupJournalReviewPanel({ apiBaseUrl, workspaceId, signalId, model }: SetupJournalReviewPanelProps) {
  const signal = model.signal?.signal || null;

  return (
    <div id="journal">
      <SetupJournalPanel
        apiBaseUrl={apiBaseUrl}
        workspaceId={workspaceId}
        signalId={signalId}
        analysisRunId={signal?.analysis_run_id || model.setupContext?.analysis_run_id || null}
        setupContextId={model.setupContext?.id || null}
        entries={model.journalEntries}
      />
    </div>
  );
}
