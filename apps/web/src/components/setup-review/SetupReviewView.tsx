import { WorkflowLinks } from "@/components/layout/workflow-links";
import { SetupEmptySection } from "@/components/setup-detail/SetupEmptySection";
import { SetupErrorSection } from "@/components/setup-detail/SetupErrorSection";
import { SetupVisualPanel } from "@/components/setup-detail/SetupVisualPanel";
import { composeSetupReview } from "@/lib/setup-review/composeSetupReview";
import type { SetupDetailData } from "@/lib/setup-detail/types";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
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
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0)}>
          <SetupEmptySection title="Setup not available" message="No setup, signal, or report payload was returned for this identifier." />
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
        <SetupReviewHeader model={model} />
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
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="space-y-6">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(3)}>
            <SetupVisualPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(4)}>
            <SetupContextReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(5)}>
            <SetupEvidenceReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(6)}>
            <SetupWaitAvoidReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(7)}>
            <SetupHistoricalReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(8)}>
            <SetupReasoningReviewPanel model={model} />
          </AnimatedListItem>
        </main>
        <aside className="space-y-6 xl:sticky xl:top-56 xl:self-start">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(3)}>
            <SetupIntelligenceContextPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(4)}>
            <SetupJournalReviewPanel
              workspaceId={workspaceId}
              signalId={data.signalId}
              model={model}
            />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(5)}>
            <SetupAuditReviewPanel model={model} />
          </AnimatedListItem>
        </aside>
      </div>
    </AnimatedSection>
  );
}
