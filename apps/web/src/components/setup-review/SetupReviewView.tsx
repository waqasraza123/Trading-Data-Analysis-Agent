import { WorkflowLinks } from "@/components/layout/workflow-links";
import { SetupEmptySection } from "@/components/setup-detail/SetupEmptySection";
import { SetupErrorSection } from "@/components/setup-detail/SetupErrorSection";
import { SetupVisualPanel } from "@/components/setup-detail/SetupVisualPanel";
import { composeSetupReview } from "@/lib/setup-review/composeSetupReview";
import type { SetupDetailData } from "@/lib/setup-detail/types";
import { AnimatedListItem, AnimatedSection, motionRevealStyle } from "@/lib/ui/motion";
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
        <AnimatedListItem as="section" style={motionRevealStyle(0, 45)}>
          <SetupEmptySection title="Setup not available" message="No setup, signal, or report payload was returned for this identifier." />
        </AnimatedListItem>
        <AnimatedListItem as="section" style={motionRevealStyle(1, 45)}>
          <SetupErrorSection failures={model.failures} />
        </AnimatedListItem>
      </AnimatedSection>
    );
  }

  return (
    <AnimatedSection as="section" className="space-y-6">
      <AnimatedListItem as="section" style={motionRevealStyle(0, 45)}>
        <SetupReviewHeader model={model} />
      </AnimatedListItem>
      <AnimatedListItem as="section" style={motionRevealStyle(1, 45)}>
        <WorkflowLinks
          workspaceId={workspaceId}
          targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review", "journal"]}
        />
      </AnimatedListItem>
      <AnimatedListItem as="section" style={motionRevealStyle(2, 45)}>
        <SetupErrorSection failures={model.failures.filter((failure) => !failure.missing)} />
      </AnimatedListItem>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="space-y-6">
          <AnimatedListItem as="section" style={motionRevealStyle(3, 45)}>
            <SetupVisualPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(4, 45)}>
            <SetupContextReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(5, 45)}>
            <SetupEvidenceReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(6, 45)}>
            <SetupWaitAvoidReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(7, 45)}>
            <SetupHistoricalReviewPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(8, 45)}>
            <SetupReasoningReviewPanel model={model} />
          </AnimatedListItem>
        </main>
        <aside className="space-y-6 xl:sticky xl:top-56 xl:self-start">
          <AnimatedListItem as="section" style={motionRevealStyle(3, 45)}>
            <SetupIntelligenceContextPanel model={model} />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(4, 45)}>
            <SetupJournalReviewPanel
              apiBaseUrl={data.apiBaseUrl}
              workspaceId={workspaceId}
              signalId={data.signalId}
              model={model}
            />
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealStyle(5, 45)}>
            <SetupAuditReviewPanel model={model} />
          </AnimatedListItem>
        </aside>
      </div>
    </AnimatedSection>
  );
}
