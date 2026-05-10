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
import { SetupVisualPanel } from "@/components/setup-detail/SetupVisualPanel";
import { SetupZonesPanel } from "@/components/setup-detail/SetupZonesPanel";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { composeSetupDetail } from "@/lib/setup-detail/composeSetupDetail";
import type { SetupDetailData } from "@/lib/setup-detail/types";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";

type SetupDetailViewProps = {
  data: SetupDetailData;
};

export function SetupDetailView({ data }: SetupDetailViewProps) {
  const model = composeSetupDetail(data);
  const signal = model.signal?.signal || null;
  const workspaceId = signal?.workspace_id || model.setupContext?.workspace_id || model.report?.workspace_id || null;

  if (!model.signal && !model.report && !model.setupContext) {
    return (
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0)}>
          <SetupEmptySection title="Signal not available" message="No setup, signal, or report payload was returned for this identifier." />
        </AnimatedListItem>
        <AnimatedListItem as="section" style={motionRevealDensityStyle(1)}>
          <SetupErrorSection failures={model.failures} />
        </AnimatedListItem>
      </AnimatedSection>
    );
  }

  return (
    <AnimatedSection as="section" className="space-y-6">
      <AnimatedListItem as="section" style={motionRevealDensityStyle(0)}>
        <SetupDetailHeader header={model.header} />
      </AnimatedListItem>
      <AnimatedListItem as="section" style={motionRevealDensityStyle(1)}>
        <WorkflowLinks
          workspaceId={workspaceId}
          targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review", "journal"]}
        />
      </AnimatedListItem>
      <AnimatedListItem as="section" style={motionRevealDensityStyle(2)}>
        <SetupErrorSection failures={model.failures.filter((failure) => !failure.missing)} />
      </AnimatedListItem>
      <AnimatedListItem as="section" style={motionRevealDensityStyle(3)}>
        <SetupVisualPanel model={model} />
      </AnimatedListItem>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <main className="space-y-6">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(4)}>
            <SetupBiasSummary model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(5)}>
            <SetupZonesPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(6)}>
            <SetupEvidencePanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(7)}>
            <SetupConflictPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(8)}>
            <SetupWaitAvoidPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(9)}>
            <SetupOutcomeHistoryPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(10)}>
            <SetupHistoricalCasesPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(11)}>
            <SetupReasoningPanel model={model} />
          </AnimatedListItem>
        </main>
        <aside className="space-y-6">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(4)}>
            <SetupQualityPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(5)}>
            <SetupDataQualityPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(6)}>
            <SetupActionPlanPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(7)}>
            <SetupAuditPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(8)}>
            <SetupJournalPanel
              workspaceId={workspaceId}
              signalId={data.signalId}
              analysisRunId={signal?.analysis_run_id || model.setupContext?.analysis_run_id || null}
              setupContextId={model.setupContext?.id || null}
              entries={model.journalEntries}
            />
          </AnimatedListItem>
        </aside>
      </div>
    </AnimatedSection>
  );
}
