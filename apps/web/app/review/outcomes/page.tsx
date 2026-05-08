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
import { AnimatedSection } from "@/lib/ui/motion";
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
        <ReviewSurfaceHero
          eyebrow="Daily outcome review"
          title="Observed outcomes"
          description="Review deterministic outcome observations, linked setup context, and reflection gaps without account-result or advice language."
          actions={
            <>
              <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
              <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "journal", "triage", "quality", "brief"]} />
            </>
          }
        />
        {!data.workspace ? (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before the outcome review loop can load."
          />
        ) : (
          <>
            <OutcomeReviewSummary data={data} />
            <OutcomeReviewFilters data={data} />
            <OutcomeReviewErrorState failures={data.failures} />
            <OutcomeReviewJournalPrompts data={data} />
            <OutcomeReviewDiagnostics data={data} />
            <OutcomeReviewQueueTable data={data} />
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
