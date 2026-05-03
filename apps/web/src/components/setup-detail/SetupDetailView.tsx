import { SetupActionPlanPanel } from "@/components/setup-detail/SetupActionPlanPanel";
import { SetupAuditPanel } from "@/components/setup-detail/SetupAuditPanel";
import { SetupBiasSummary } from "@/components/setup-detail/SetupBiasSummary";
import { SetupConflictPanel } from "@/components/setup-detail/SetupConflictPanel";
import { SetupDataQualityPanel } from "@/components/setup-detail/SetupDataQualityPanel";
import { SetupDetailHeader } from "@/components/setup-detail/SetupDetailHeader";
import { SetupEmptySection } from "@/components/setup-detail/SetupEmptySection";
import { SetupErrorSection } from "@/components/setup-detail/SetupErrorSection";
import { SetupEvidencePanel } from "@/components/setup-detail/SetupEvidencePanel";
import { SetupHistoricalCasesPanel } from "@/components/setup-detail/SetupHistoricalCasesPanel";
import { SetupJournalPanel } from "@/components/setup-detail/SetupJournalPanel";
import { SetupOutcomeHistoryPanel } from "@/components/setup-detail/SetupOutcomeHistoryPanel";
import { SetupQualityPanel } from "@/components/setup-detail/SetupQualityPanel";
import { SetupReasoningPanel } from "@/components/setup-detail/SetupReasoningPanel";
import { SetupWaitAvoidPanel } from "@/components/setup-detail/SetupWaitAvoidPanel";
import { SetupZonesPanel } from "@/components/setup-detail/SetupZonesPanel";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { composeSetupDetail } from "@/lib/setup-detail/composeSetupDetail";
import type { SetupDetailData } from "@/lib/setup-detail/types";

type SetupDetailViewProps = {
  data: SetupDetailData;
};

export function SetupDetailView({ data }: SetupDetailViewProps) {
  const model = composeSetupDetail(data);
  const signal = model.signal?.signal || null;
  const workspaceId = signal?.workspace_id || model.setupContext?.workspace_id || model.report?.workspace_id || null;

  if (!model.signal && !model.report && !model.setupContext) {
    return (
      <div className="space-y-6">
        <SetupEmptySection title="Signal not available" message="No setup, signal, or report payload was returned for this identifier." />
        <SetupErrorSection failures={model.failures} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SetupDetailHeader header={model.header} />
      <WorkflowLinks workspaceId={workspaceId} targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review", "journal"]} />
      <SetupErrorSection failures={model.failures.filter((failure) => !failure.missing)} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <main className="space-y-6">
          <SetupBiasSummary model={model} />
          <SetupZonesPanel model={model} />
          <SetupEvidencePanel model={model} />
          <SetupConflictPanel model={model} />
          <SetupWaitAvoidPanel model={model} />
          <SetupOutcomeHistoryPanel model={model} />
          <SetupHistoricalCasesPanel model={model} />
          <SetupReasoningPanel model={model} />
        </main>
        <aside className="space-y-6">
          <SetupQualityPanel model={model} />
          <SetupDataQualityPanel model={model} />
          <SetupActionPlanPanel model={model} />
          <SetupAuditPanel model={model} />
          <SetupJournalPanel
            apiBaseUrl={data.apiBaseUrl}
            workspaceId={workspaceId}
            signalId={data.signalId}
            analysisRunId={signal?.analysis_run_id || model.setupContext?.analysis_run_id || null}
            setupContextId={model.setupContext?.id || null}
            entries={model.journalEntries}
          />
        </aside>
      </div>
    </div>
  );
}
