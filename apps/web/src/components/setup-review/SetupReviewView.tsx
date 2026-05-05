import { WorkflowLinks } from "@/components/layout/workflow-links";
import { SetupEmptySection } from "@/components/setup-detail/SetupEmptySection";
import { SetupErrorSection } from "@/components/setup-detail/SetupErrorSection";
import { SetupVisualPanel } from "@/components/setup-detail/SetupVisualPanel";
import { composeSetupReview } from "@/lib/setup-review/composeSetupReview";
import type { SetupDetailData } from "@/lib/setup-detail/types";
import { SetupAuditReviewPanel } from "./SetupAuditReviewPanel";
import { SetupContextReviewPanel } from "./SetupContextReviewPanel";
import { SetupEvidenceReviewPanel } from "./SetupEvidenceReviewPanel";
import { SetupHistoricalReviewPanel } from "./SetupHistoricalReviewPanel";
import { SetupIntelligenceContextPanel } from "./SetupIntelligenceContextPanel";
import { SetupJournalReviewPanel } from "./SetupJournalReviewPanel";
import { SetupReasoningReviewPanel } from "./SetupReasoningReviewPanel";
import { SetupReviewHeader } from "./SetupReviewHeader";
import { SetupWaitAvoidReviewPanel } from "./SetupWaitAvoidReviewPanel";

type SetupReviewViewProps = {
  data: SetupDetailData;
};

export function SetupReviewView({ data }: SetupReviewViewProps) {
  const model = composeSetupReview(data);
  const signal = model.signal?.signal || null;
  const workspaceId = signal?.workspace_id || model.setupContext?.workspace_id || model.report?.workspace_id || null;

  if (!model.signal && !model.report && !model.setupContext) {
    return (
      <div className="space-y-6">
        <SetupEmptySection title="Setup not available" message="No setup, signal, or report payload was returned for this identifier." />
        <SetupErrorSection failures={model.failures} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SetupReviewHeader model={model} />
      <WorkflowLinks workspaceId={workspaceId} targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review", "journal"]} />
      <SetupErrorSection failures={model.failures.filter((failure) => !failure.missing)} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="space-y-6">
          <SetupVisualPanel model={model} />
          <SetupContextReviewPanel model={model} />
          <SetupEvidenceReviewPanel model={model} />
          <SetupWaitAvoidReviewPanel model={model} />
          <SetupHistoricalReviewPanel model={model} />
          <SetupReasoningReviewPanel model={model} />
        </main>
        <aside className="space-y-6 xl:sticky xl:top-56 xl:self-start">
          <SetupIntelligenceContextPanel model={model} />
          <SetupJournalReviewPanel
            apiBaseUrl={data.apiBaseUrl}
            workspaceId={workspaceId}
            signalId={data.signalId}
            model={model}
          />
          <SetupAuditReviewPanel model={model} />
        </aside>
      </div>
    </div>
  );
}
