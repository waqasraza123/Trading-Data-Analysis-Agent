import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/empty-states/empty-state";
import { OutcomeReviewFilters } from "@/components/outcome-review/OutcomeReviewFilters";
import {
  OutcomeReviewDiagnostics,
  OutcomeReviewJournalPrompts,
  OutcomeReviewSummary,
} from "@/components/outcome-review/OutcomeReviewInsights";
import { OutcomeReviewQueueTable } from "@/components/outcome-review/OutcomeReviewQueueTable";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { ReviewSurfaceHero } from "@/components/review-surfaces/ReviewSurface";
import { OutcomeReviewErrorState } from "@/components/review/OutcomeReviewErrorState";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
import { getOutcomeReviewData } from "@/lib/api/outcomeReview";

type OutcomeReviewPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function OutcomeReviewPage({ searchParams }: OutcomeReviewPageProps) {
  const params = await searchParams;
  const data = await getOutcomeReviewData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <ReviewSurfaceHero
            eyebrow="Daily outcome review"
            title="Observed outcomes"
            description="Review deterministic outcome observations, linked setup context, and reflection gaps without account-result or advice language."
            actions={
              <>
                <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
                <WorkflowLinks
                  workspaceId={data.workspace?.id}
                  targets={["commandCenter", "journal", "triage", "quality", "brief"]}
                />
              </>
            }
          />
        </AnimatedListItem>
        {!data.workspace ? (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <EmptyState
              title="No workspace available"
              message="Seed or create a workspace in the API before the outcome review loop can load."
            />
          </AnimatedListItem>
        ) : (
          <>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "regular")}>
              <OutcomeReviewSummary data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
              <OutcomeReviewFilters data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
              <OutcomeReviewErrorState failures={data.failures} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
              <OutcomeReviewJournalPrompts data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "compact")}>
              <OutcomeReviewDiagnostics data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(7, "compact")}>
              <OutcomeReviewQueueTable data={data} />
            </AnimatedListItem>
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
